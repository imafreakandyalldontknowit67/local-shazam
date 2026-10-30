use crate::{
    audio,
    dsp::Landmark,
    store::{Store, ENGINE},
};
use anyhow::{bail, Context, Result};
use crossbeam_channel::bounded;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeSet,
    fs::File,
    io::Read,
    path::{Path, PathBuf},
    thread,
    time::{Instant, UNIX_EPOCH},
};
use walkdir::WalkDir;

const AUDIO:&str="mp3 flac wav ogg opus m4a aac wma alac aiff aif ape wv mpc mp4 mkv webm 3gp 3g2 mov avi aifc caf au snd w64 rf64 oga mka ac3 eac3 dts dtshd amr awb m4b m4p mp2 mpa mpga tta tak shn dsf dff dsd aob vob mts m2ts";
const OTHER:&str="db db-wal db-shm jpg jpeg png gif webp pdf txt log cue m3u m3u8 nfo json xml ini lrc srt md exe dll zip rar 7z";
pub fn normalize(path: &Path) -> Result<PathBuf> {
    let absolute = if path.exists() {
        path.canonicalize()?
    } else {
        std::path::absolute(path)?
    };
    #[cfg(windows)]
    {
        let text = absolute
            .to_str()
            .context("Windows paths with unpaired UTF-16 surrogates are unsupported")?;
        if let Some(rest) = text.strip_prefix(r"\\?\UNC\") {
            return Ok(PathBuf::from(format!(r"\\{rest}")));
        }
        if let Some(rest) = text.strip_prefix(r"\\?\") {
            return Ok(PathBuf::from(rest));
        }
    }
    Ok(absolute)
}

fn extension(path: &Path) -> String {
    path.extension()
        .unwrap_or_default()
        .to_string_lossy()
        .to_ascii_lowercase()
}
fn known(path: &Path) -> bool {
    let ext = extension(path);
    AUDIO.split_whitespace().any(|x| x == ext)
}
pub fn identity(path: &Path, fan: usize) -> Result<String> {
    let meta = path.metadata()?;
    let modified = meta.modified()?.duration_since(UNIX_EPOCH)?.as_nanos();
    let mut bytes = vec![0; 8192];
    let mut file = File::open(path)?;
    let count = file.read(&mut bytes)?;
    bytes.truncate(count);
    Ok(format!(
        "{ENGINE}:fan{fan}:{}:{modified}:{:x}",
        meta.len(),
        Sha256::digest(bytes)
    ))
}
#[derive(Debug, Serialize)]
pub struct Failure {
    pub filepath: PathBuf,
    pub error: String,
}
#[derive(Debug, Serialize, Default)]
pub struct Report {
    pub total: usize,
    pub indexed: usize,
    pub skipped: usize,
    pub ignored: usize,
    pub failed: usize,
    pub seconds: f64,
    pub errors: Vec<Failure>,
}
struct Job {
    path: PathBuf,
    identity: String,
}
struct Completed {
    job: Job,
    data: Result<Option<(Vec<Landmark>, f64)>>,
}

pub fn bootstrap(
    directories: &[PathBuf],
    db: &mut Store,
    workers: usize,
    fan: usize,
    force: bool,
    progress: bool,
) -> Result<Report> {
    if !(1..=64).contains(&workers) {
        bail!("workers must be between 1 and 64");
    }
    let start = Instant::now();
    let mut paths = BTreeSet::new();
    for directory in directories {
        if !directory.is_dir() {
            bail!("Not a directory: {}", directory.display());
        }
        for entry in WalkDir::new(directory).into_iter().filter_entry(|e| {
            !e.file_type().is_dir()
                || !matches!(
                    e.file_name().to_str(),
                    Some(".git" | ".venv" | "target" | "__pycache__")
                )
        }) {
            let entry = entry.with_context(|| format!("Scanning {}", directory.display()))?;
            if !entry.file_type().is_file() {
                continue;
            }
            if OTHER
                .split_whitespace()
                .any(|e| e == extension(entry.path()))
            {
                continue;
            }
            paths.insert(normalize(entry.path())?);
        }
    }
    let existing = db.identities()?;
    let mut report = Report {
        total: paths.len(),
        ..Report::default()
    };
    let mut jobs = vec![];
    for path in paths {
        match identity(&path, fan) {
            Ok(identity) => {
                if !force && existing.get(path.to_string_lossy().as_ref()) == Some(&identity) {
                    report.skipped += 1;
                } else {
                    jobs.push(Job { path, identity });
                }
            }
            Err(e) => {
                report.failed += 1;
                report.errors.push(Failure {
                    filepath: path,
                    error: format!("{e:#}"),
                });
            }
        }
    }
    let (job_tx, job_rx) = bounded::<Job>(workers * 2);
    let (out_tx, out_rx) = bounded::<Completed>(workers);
    thread::scope(|scope| {
        scope.spawn(move || {
            for job in jobs {
                if job_tx.send(job).is_err() {
                    break;
                }
            }
        });
        for _ in 0..workers {
            let rx = job_rx.clone();
            let tx = out_tx.clone();
            scope.spawn(move || {
                for job in rx {
                    let data = (|| -> Result<_> {
                        if !known(&job.path) && !audio::has_audio(&job.path)? {
                            return Ok(None);
                        }
                        let (hashes, duration) = audio::fingerprint(&job.path, fan)?;
                        if hashes.is_empty() {
                            bail!("No usable landmarks (silent or too-short audio)");
                        }
                        if identity(&job.path, fan)? != job.identity {
                            bail!("File changed during indexing; retry it");
                        }
                        Ok(Some((hashes, duration)))
                    })();
                    if tx.send(Completed { job, data }).is_err() {
                        break;
                    }
                }
            });
        }
        drop(out_tx);
        drop(job_rx);
        for done in out_rx {
            let result = match done.data {
                Ok(Some((mut hashes, duration))) => db
                    .insert(&done.job.path, &done.job.identity, duration, &mut hashes)
                    .map(|()| true),
                Ok(None) => {
                    report.ignored += 1;
                    Ok(false)
                }
                Err(e) => Err(e),
            };
            match result {
                Ok(true) => report.indexed += 1,
                Ok(false) => {}
                Err(e) => {
                    report.failed += 1;
                    report.errors.push(Failure {
                        filepath: done.job.path,
                        error: format!("{e:#}"),
                    });
                }
            }
            if progress {
                eprint!(
                    "\rIndexed: {} | skipped: {} | ignored: {} | failed: {}",
                    report.indexed, report.skipped, report.ignored, report.failed
                );
            }
        }
    });
    if progress {
        eprintln!();
    }
    report.seconds = start.elapsed().as_secs_f64();
    Ok(report)
}
