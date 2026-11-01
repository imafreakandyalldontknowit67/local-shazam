use anyhow::{bail, Result};
use clap::{Parser, Subcommand, ValueEnum};
use local_shazam::{audio, index, store::Store};
use std::{
    io::{self, Write},
    path::{Path, PathBuf},
};

#[derive(Clone, Copy, Debug, PartialEq, Eq, ValueEnum)]
enum Backend {
    Olaf,
    Rust,
}

#[derive(Parser)]
#[command(
    version,
    about = "Identify snippets against your own local audio library. No Python or cloud API."
)]
struct Args {
    /// Recognition backend. Olaf is experimental; Rust remains available.
    #[arg(long, global = true, value_enum, default_value_t=Backend::Olaf)]
    backend: Backend,
    /// Separate versioned Olaf index directory (never a Rust .db file).
    #[arg(long, global = true)]
    olaf_index: Option<PathBuf>,
    /// Olaf executable to seed a NEW index runtime.
    #[arg(long, global = true)]
    olaf_bin: Option<PathBuf>,
    /// Database path. Defaults to local-shazam.db next to the executable.
    #[arg(long, global = true)]
    db: Option<PathBuf>,
    /// Machine-readable output for CLI commands.
    #[arg(long, global = true)]
    json: bool,
    #[command(subcommand)]
    command: Option<Action>,
}
#[derive(Subcommand)]
enum Action {
    /// Index complete audio files from folders (incremental).
    #[command(alias = "add", alias = "index")]
    Bootstrap {
        #[arg(required = true)]
        directories: Vec<PathBuf>,
        /// Parallel workers (1-64). Defaults to at most 6; larger values are not established safe.
        #[arg(short='w',long,default_value_t=default_workers(),value_parser=clap::value_parser!(u16).range(1..=64))]
        workers: u16,
        /// Reduce landmark fan-out. Saves storage but can weaken short-snippet matches.
        #[arg(long)]
        compact: bool,
        /// Reindex unchanged files, too.
        #[arg(long)]
        force: bool,
    },
    /// Match one or more snippets.
    Match {
        #[arg(required = true)]
        snippets: Vec<PathBuf>,
        #[arg(short='n',long,default_value_t=10,value_parser=clap::value_parser!(u16).range(1..))]
        top: u16,
    },
    /// Show database statistics.
    Status,
    /// Remove a song or indexed directory.
    Remove { path: PathBuf },
    /// Reclaim unused database pages without reducing fingerprints.
    CompactDb,
    /// Export hashes for validation and diagnostics.
    Fingerprint {
        path: PathBuf,
        #[arg(long,default_value_t=5,value_parser=clap::value_parser!(u16).range(1..=128))]
        fan: u16,
    },
}
fn default_workers() -> u16 {
    workers_for_parallelism(std::thread::available_parallelism().ok().map(|n| n.get()))
}
fn workers_for_parallelism(logical_cpus: Option<usize>) -> u16 {
    logical_cpus.unwrap_or(4).clamp(1, 6) as u16
}
struct Paths {
    db: PathBuf,
    olaf_index: PathBuf,
    olaf_bin: PathBuf,
}
impl Args {
    fn paths(&self, executable: &Path) -> Result<Paths> {
        if self.backend == Backend::Olaf && self.db.is_some() {
            bail!("--db is for Rust. Use --backend rust --db PATH, or --olaf-index DIRECTORY for Olaf.");
        }
        Ok(Paths {
            db: self
                .db
                .clone()
                .unwrap_or_else(|| executable.with_file_name("local-shazam.db")),
            olaf_index: self
                .olaf_index
                .clone()
                .unwrap_or_else(|| executable.with_file_name("local-olaf")),
            olaf_bin: self.olaf_bin.clone().unwrap_or_else(|| {
                executable
                    .with_file_name("olaf-runtime")
                    .join(local_shazam::olaf::runtime_name())
            }),
        })
    }
}
fn uses_rust(backend: Backend, action: &Action) -> bool {
    backend == Backend::Rust || matches!(action, Action::Fingerprint { .. })
}
fn print_stats(db: &Path, json: bool) -> Result<()> {
    let stats = Store::open(db, false)?.stats()?;
    if json {
        println!("{}", serde_json::to_string(&stats)?);
    } else {
        println!(
            "Songs: {}\nFingerprints: {}\nDatabase: {:.1} MiB\n{}",
            stats.songs,
            stats.fingerprints,
            stats.bytes as f64 / 1048576.0,
            db.display()
        );
    }
    Ok(())
}
fn run_rust(action: Action, db: &Path, json: bool) -> Result<()> {
    match action {
        Action::Bootstrap {
            directories,
            workers,
            compact,
            force,
        } => {
            let mut store = Store::open(db, true)?;
            let report = index::bootstrap(
                &directories,
                &mut store,
                workers as usize,
                if compact { 3 } else { 5 },
                force,
                !json,
            )?;
            if json {
                println!("{}", serde_json::to_string(&report)?);
            } else {
                println!(
                    "Indexed: {} | skipped: {} | ignored: {} | failed: {} | {:.2}s",
                    report.indexed, report.skipped, report.ignored, report.failed, report.seconds
                );
                for error in &report.errors {
                    eprintln!("{}: {}", error.filepath.display(), error.error);
                }
            }
            if report.failed > 0 {
                bail!(
                    "{} files failed; successful songs were saved",
                    report.failed
                );
            }
        }
        Action::Match { snippets, top } => {
            let store = Store::open(db, false)?;
            let mut output = vec![];
            for snippet in snippets {
                let (hashes, _) = audio::fingerprint(&snippet, 5)?;
                let matches = store.matches(&hashes, top as usize)?;
                if !json {
                    println!("\nAnalyzing: {}", snippet.display());
                    if matches.is_empty() {
                        println!("No matches found.");
                    }
                    for (i, m) in matches.iter().enumerate() {
                        let label = if m.confidence >= 0.2 {
                            "HIGH"
                        } else if m.confidence >= 0.1 {
                            "PROBABLE"
                        } else if m.confidence >= 0.05 {
                            "POSSIBLE"
                        } else {
                            "LOW"
                        };
                        println!(
                            "#{} {:5.1}% [{}] {} aligned hashes at {:.2}s\n    {}\n    {}",
                            i + 1,
                            m.confidence * 100.0,
                            label,
                            m.aligned_hashes,
                            m.offset_seconds,
                            m.filename,
                            m.filepath
                        );
                    }
                }
                output.push(serde_json::json!({"snippet":snippet,"matches":matches}));
            }
            if json {
                println!("{}", serde_json::to_string(&output)?);
            }
        }
        Action::Status => print_stats(db, json)?,
        Action::CompactDb => {
            if !db.exists() {
                bail!("Database does not exist: {}", db.display());
            }
            Store::open(db, true)?.compact()?;
            print_stats(db, json)?;
        }
        Action::Remove { path } => {
            if !db.exists() {
                bail!("Database does not exist: {}", db.display());
            }
            let path = index::normalize(&path)?;
            let count = Store::open(db, true)?.remove(&path)?;
            if json {
                println!("{}", serde_json::json!({"removed":count}));
            } else {
                println!("Removed {count} songs");
            }
        }
        Action::Fingerprint { path, fan } => {
            let (hashes, duration) = audio::fingerprint(&path, fan as usize)?;
            println!(
                "{}",
                serde_json::json!({"duration":duration,"hashes":hashes})
            );
        }
    }
    Ok(())
}
fn run(
    action: Action,
    db: &Path,
    json: bool,
    backend: Backend,
    olaf_index: &Path,
    olaf_bin: &Path,
) -> Result<()> {
    if uses_rust(backend, &action) {
        return run_rust(action, db, json);
    }
    // Reject unsupported options before opening or creating any Olaf index.
    match &action {
        Action::Bootstrap { compact: true, .. } => bail!("--compact is a Rust-only extraction option; Olaf uses a versioned two-peak profile"),
        Action::Remove { .. } | Action::CompactDb => bail!("This maintenance command currently supports --backend rust only. Olaf indexes are separate; no data was changed."),
        _ => {}
    }
    let mut engine = local_shazam::olaf::Backend::open(
        olaf_index,
        olaf_bin,
        matches!(action, Action::Bootstrap { .. }),
    )?;
    match action {
        Action::Bootstrap {
            directories,
            workers,
            force,
            ..
        } => {
            let report = engine.bootstrap(&directories, workers, force, !json)?;
            if json {
                println!("{}", serde_json::to_string(&report)?);
            } else {
                println!(
                    "Olaf indexed {}, skipped {}, failed {} in {:.2}s",
                    report.indexed, report.skipped, report.failed, report.seconds
                );
            }
            for e in &report.errors {
                eprintln!("{}: {}", e.filepath.display(), e.error);
            }
            if report.failed > 0 {
                bail!(
                    "Some files failed; successful batches were saved. Retry indexing to resume."
                );
            }
        }
        Action::Match { snippets, top } => {
            let mut results = Vec::new();
            for snippet in snippets {
                let result = engine.recognize(&snippet, top as usize)?;
                if !json {
                    println!(
                        "\n{}: {}",
                        snippet.display(),
                        result.status.replace('_', " ")
                    );
                    for (i, c) in result.matches.iter().enumerate() {
                        println!(
                            "#{} [{}] {}\n    {:.2}s | {} supporting moments over {:.2}s",
                            i + 1,
                            c.label,
                            c.path,
                            c.offset_seconds,
                            c.anchors,
                            c.evidence_span_seconds
                        );
                    }
                    if result.matches.is_empty() {
                        println!("Try a longer or clearer snippet; no candidates met the evidence requirements.");
                    }
                    for warning in &result.warnings {
                        eprintln!("Note: {warning}");
                    }
                }
                results.push(result);
            }
            if json {
                println!("{}", serde_json::to_string(&results)?);
            }
        }
        Action::Status => {
            let stats = engine.status();
            if json {
                println!("{stats}");
            } else {
                println!("Olaf index: {}\nSongs: {}\nDatabase: {:.2} MiB\nExperimental candidate verification enabled", olaf_index.display(),stats["songs"],stats["bytes"].as_u64().unwrap_or(0) as f64/1048576.);
            }
        }
        Action::Remove { .. } | Action::CompactDb => unreachable!(),
        Action::Fingerprint { .. } => unreachable!(),
    }
    Ok(())
}
fn parse_workers(input: &str) -> Result<Option<u16>> {
    let value = input.trim();
    if value.eq_ignore_ascii_case("q") {
        return Ok(None);
    }
    if value.is_empty() {
        return Ok(Some(default_workers()));
    }
    match value.parse::<u16>() {
        Ok(n) if (1..=64).contains(&n) => Ok(Some(n)),
        _ => bail!("Enter a worker count from 1 to 64, or q to cancel"),
    }
}
fn choose_workers() -> Result<Option<u16>> {
    println!("\nWorkers: 2 = lighter background use; {} = default (capped at 6). Larger selections increase resource use and are not established safe.",default_workers());
    loop {
        print!(
            "Worker count [1-64, Enter = {}, q = cancel]: ",
            default_workers()
        );
        io::stdout().flush()?;
        let mut input = String::new();
        if io::stdin().read_line(&mut input)? == 0 {
            return Ok(None);
        }
        match parse_workers(&input) {
            Ok(n) => return Ok(n),
            Err(e) => eprintln!("{e}"),
        }
    }
}
fn menu(db: &Path, backend: Backend, olaf_index: &Path, olaf_bin: &Path) -> Result<()> {
    println!("\n  Local Shazam");
    loop {
        print!("\n  [1] Add a music folder\n  [2] Identify audio clips\n  [3] View library stats\n  [4] Exit\n\n  Choose an option: ");
        io::stdout().flush()?;
        let mut choice = String::new();
        if io::stdin().read_line(&mut choice)? == 0 {
            break;
        }
        let action = match choice.trim() {
            "1" => {
                if let Some(folder) = rfd::FileDialog::new()
                    .set_title("Select your music folder")
                    .pick_folder()
                {
                    choose_workers()?.map(|workers| Action::Bootstrap {
                        directories: vec![folder],
                        workers,
                        compact: false,
                        force: false,
                    })
                } else {
                    None
                }
            }
            "2" => rfd::FileDialog::new()
                .set_title("Select audio snippet(s) to identify")
                .pick_files()
                .map(|snippets| Action::Match { snippets, top: 10 }),
            "3" => Some(Action::Status),
            "4" => break,
            _ => {
                println!("Invalid option.");
                continue;
            }
        };
        if let Some(action) = action {
            if let Err(e) = run(action, db, false, backend, olaf_index, olaf_bin) {
                eprintln!("Error: {e:#}");
            }
        } else {
            println!("Cancelled.");
        }
    }
    Ok(())
}
fn main() {
    let args = Args::parse();
    let result = (|| -> Result<()> {
        let Paths {
            db,
            olaf_index,
            olaf_bin,
        } = args.paths(&std::env::current_exe()?)?;
        if let Some(action) = args.command {
            run(action, &db, args.json, args.backend, &olaf_index, &olaf_bin)
        } else {
            menu(&db, args.backend, &olaf_index, &olaf_bin)
        }
    })();
    if let Err(e) = result {
        eprintln!("Error: {e:#}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn default_workers_are_capped_on_every_machine() {
        for cpus in [0, 1, 2, 4, 6, 7, 64, 256, usize::MAX] {
            assert_eq!(workers_for_parallelism(Some(cpus)), cpus.clamp(1, 6) as u16);
        }
        assert_eq!(workers_for_parallelism(None), 4);
        assert!((1..=6).contains(&default_workers()));
    }
    #[test]
    fn worker_selection_bounds_and_cancel() {
        assert_eq!(parse_workers("12").unwrap(), Some(12));
        assert_eq!(parse_workers(" 1 ").unwrap(), Some(1));
        assert_eq!(parse_workers("64").unwrap(), Some(64));
        assert_eq!(parse_workers("").unwrap(), Some(default_workers()));
        assert_eq!(parse_workers("q").unwrap(), None);
        assert_eq!(parse_workers(" Q ").unwrap(), None);
        for invalid in ["0", "65", "65536", "-1", "garbage"] {
            assert!(parse_workers(invalid).is_err());
        }
    }
    #[test]
    fn cli_worker_bounds_and_aliases_match_menu() {
        for alias in ["bootstrap", "add", "index"] {
            let args = Args::try_parse_from(["local-shazam", alias, "music"]).unwrap();
            let Some(Action::Bootstrap { workers, .. }) = args.command else {
                panic!("wrong action")
            };
            assert_eq!(workers, default_workers());
        }
        for value in ["1", "6", "12", "64"] {
            let args =
                Args::try_parse_from(["local-shazam", "bootstrap", "music", "--workers", value])
                    .unwrap();
            let Some(Action::Bootstrap { workers, .. }) = args.command else {
                panic!("wrong action")
            };
            assert_eq!(workers, value.parse::<u16>().unwrap());
        }
        for value in ["0", "65", "65536", "-1", "invalid"] {
            assert!(Args::try_parse_from([
                "local-shazam",
                "bootstrap",
                "music",
                "--workers",
                value
            ])
            .is_err());
        }
    }
    #[test]
    fn defaults_are_olaf_first_with_separate_package_paths() {
        let args = Args::try_parse_from(["local-shazam", "status"]).unwrap();
        assert_eq!(args.backend, Backend::Olaf);
        assert!(!uses_rust(args.backend, args.command.as_ref().unwrap()));
        let package = Path::new("release package");
        let executable = package.join(if cfg!(windows) {
            "local-shazam.exe"
        } else {
            "local-shazam"
        });
        let paths = args.paths(&executable).unwrap();
        assert_eq!(paths.db, package.join("local-shazam.db"));
        assert_eq!(paths.olaf_index, package.join("local-olaf"));
        assert_eq!(
            paths.olaf_bin,
            package
                .join("olaf-runtime")
                .join(local_shazam::olaf::runtime_name())
        );
    }
    #[test]
    fn explicit_overrides_do_not_cross_backends() {
        let executable = Path::new("package/local-shazam");
        let args = Args::try_parse_from([
            "local-shazam",
            "--olaf-index",
            "isolated index",
            "--olaf-bin",
            "custom runtime",
            "status",
        ])
        .unwrap();
        let paths = args.paths(executable).unwrap();
        assert_eq!(paths.olaf_index, Path::new("isolated index"));
        assert_eq!(paths.olaf_bin, Path::new("custom runtime"));
        let args =
            Args::try_parse_from(["local-shazam", "--db", "comparison.db", "status"]).unwrap();
        assert!(args.paths(executable).is_err());
        let args = Args::try_parse_from([
            "local-shazam",
            "--backend",
            "rust",
            "--db",
            "comparison.db",
            "status",
        ])
        .unwrap();
        assert!(uses_rust(args.backend, args.command.as_ref().unwrap()));
        assert_eq!(
            args.paths(executable).unwrap().db,
            Path::new("comparison.db")
        );
    }
    #[test]
    fn fingerprint_remains_a_rust_diagnostic() {
        let args = Args::try_parse_from(["local-shazam", "fingerprint", "snippet.wav"]).unwrap();
        assert!(uses_rust(args.backend, args.command.as_ref().unwrap()));
    }
    #[test]
    fn unsupported_olaf_actions_do_not_create_an_index() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path().join("index");
        for action in [
            Action::Bootstrap {
                directories: vec![],
                workers: 1,
                compact: true,
                force: false,
            },
            Action::CompactDb,
            Action::Remove {
                path: dir.path().join("song.wav"),
            },
        ] {
            let error = run(
                action,
                &dir.path().join("unused.db"),
                false,
                Backend::Olaf,
                &root,
                &dir.path().join("missing-runtime"),
            )
            .unwrap_err()
            .to_string();
            assert!(error.contains("Rust") || error.contains("--backend rust"));
            assert!(!root.exists());
        }
    }
    #[test]
    fn rust_status_needs_no_olaf_runtime_or_index() {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("comparison.db");
        drop(Store::open(&db, true).unwrap());
        let root = dir.path().join("unused-index");
        run(
            Action::Status,
            &db,
            true,
            Backend::Rust,
            &root,
            &dir.path().join("missing-runtime"),
        )
        .unwrap();
        assert!(!root.exists());
    }
}
