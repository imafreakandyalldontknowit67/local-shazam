//! Local Olaf subprocess backend. Rust DSP verifies candidate windows only.
//! Retrieval settings/index format and heuristic acceptance policy are versioned.
use crate::{
    audio,
    dsp::{Landmark, Stream, HOP, RATE},
    index,
};
use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet, HashMap},
    fs::{self, File},
    io::{BufReader, BufWriter, Read, Seek, SeekFrom, Write},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    thread,
    time::{Duration, Instant},
};

const VERSION: &str = "olaf-local-app-v1-twopeak-time20-verifier1";
const POLICY: &str = "candidate-window-v1-experimental";
const MAX_QUERY: f64 = 30.0;
const AUDIO: &str = "mp3 flac wav ogg opus m4a aac wma alac aiff aif ape wv mpc mp4 mkv webm 3gp 3g2 mov avi aifc caf au snd w64 rf64 oga mka ac3 eac3 dts dtshd amr awb m4b m4p mp2 mpa mpga tta tak shn dsf dff dsd aob vob mts m2ts";
/// The separately packaged runtime, never the application executable itself.
pub const fn runtime_name() -> &'static str {
    if cfg!(windows) {
        "olaf.exe"
    } else {
        "olaf"
    }
}
fn check_executable(path: &Path) -> Result<()> {
    let metadata = path
        .metadata()
        .with_context(|| format!("Cannot read Olaf runtime: {}", path.display()))?;
    if !metadata.is_file() {
        bail!("Olaf runtime is not a file: {}", path.display());
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if metadata.permissions().mode() & 0o111 == 0 {
            bail!("Olaf runtime is not executable: {}. Restore its execute permission (chmod +x) or re-extract the matching release package with permissions preserved.", path.display());
        }
    }
    Ok(())
}
fn batch_size(workers: u16) -> usize {
    (usize::from(workers) * 16).clamp(32, 512)
}
fn candidate_key(path: &str) -> String {
    // Preserve the Windows behavior, but do not merge distinct Unix filenames.
    if cfg!(windows) {
        path.to_lowercase()
    } else {
        path.to_owned()
    }
}
#[derive(Serialize, Deserialize)]
struct Manifest {
    version: String,
    binary_sha256: String,
    files: BTreeMap<String, String>,
}
#[derive(Debug, Clone, Deserialize)]
struct RawMatch {
    match_count: u64,
    query_start: f64,
    query_stop: f64,
    reference_start: f64,
    path: String,
}
#[derive(Debug, Clone, Serialize)]
pub struct Candidate {
    pub path: String,
    pub offset_seconds: f64,
    pub label: String,
    pub anchors: usize,
    pub distinct_hashes: usize,
    pub evidence_span_seconds: f64,
    pub olaf_votes: u64,
}
#[derive(Serialize)]
pub struct Recognition {
    pub snippet: PathBuf,
    pub status: String,
    pub analyzed_seconds: f64,
    pub policy: &'static str,
    pub matches: Vec<Candidate>,
    pub warnings: Vec<String>,
}
struct Process(Child);
impl Drop for Process {
    fn drop(&mut self) {
        // Unix currently reaps only the direct child below. Descendant cleanup
        // still needs process-group handling and target-specific validation.
        #[cfg(windows)]
        if matches!(self.0.try_wait(), Ok(None)) {
            // Kill only this operation's known child tree on timeout/error.
            let _ = audio::command("taskkill")
                .args(["/PID", &self.0.id().to_string(), "/T", "/F"])
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .status();
        }
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}
// Redirect output to disk, so neither a full pipe nor an unbounded stderr Vec can hang us.
fn execute(command: Command, seconds: u64, temp: &Path) -> Result<(Vec<u8>, String)> {
    let (bytes, detail, success) = execute_output(command, seconds, temp)?;
    if !success {
        bail!("Local engine failed: {detail}");
    }
    Ok((bytes, detail))
}
// Preserve per-file completion records even when another file fails.
fn execute_output(
    mut command: Command,
    seconds: u64,
    temp: &Path,
) -> Result<(Vec<u8>, String, bool)> {
    let mut out = tempfile::tempfile_in(temp)?;
    let mut err = tempfile::tempfile_in(temp)?;
    let program = command.get_program().to_string_lossy().into_owned();
    let mut child = Process(
        command
            .stdin(Stdio::null())
            .stdout(out.try_clone()?)
            .stderr(err.try_clone()?)
            .spawn().with_context(|| format!("Cannot start {program}. Check the runtime architecture, executable permissions and required programs (including FFmpeg) on PATH"))?,
    );
    let deadline = Instant::now() + Duration::from_secs(seconds);
    let status = loop {
        if let Some(s) = child.0.try_wait()? {
            break s;
        }
        if Instant::now() > deadline {
            bail!("Local audio operation timed out after {seconds}s");
        }
        thread::sleep(Duration::from_millis(10));
    };
    out.seek(SeekFrom::Start(0))?;
    err.seek(SeekFrom::Start(0))?;
    let mut detail = String::new();
    if err.metadata()?.len() > 16 * 1024 * 1024 {
        bail!("Engine diagnostics exceeded 16 MiB; no unconfirmed completions saved");
    }
    err.read_to_string(&mut detail)?;
    if out.metadata()?.len() > 16 * 1024 * 1024 {
        bail!("Engine output exceeds bounded output limit");
    }
    let mut bytes = Vec::new();
    out.read_to_end(&mut bytes)?;
    Ok((bytes, detail, status.success()))
}
fn digest(path: &Path) -> Result<String> {
    let mut f = File::open(path)?;
    let mut h = Sha256::new();
    let mut b = [0u8; 65536];
    loop {
        let n = f.read(&mut b)?;
        if n == 0 {
            break;
        }
        h.update(&b[..n]);
    }
    Ok(format!("{:x}", h.finalize()))
}
fn atomic_json(path: &Path, value: &impl Serialize) -> Result<()> {
    let mut f = tempfile::NamedTempFile::new_in(path.parent().context("Missing parent")?)?;
    // Direct serde-to-File made one OS write for many tiny JSON tokens, and
    // rewriting a large manifest every eight tracks dominated small-file work.
    {
        let mut buffered = BufWriter::with_capacity(256 * 1024, &mut f);
        serde_json::to_writer_pretty(&mut buffered, value)?;
        buffered.flush()?;
    }
    f.as_file().sync_all()?;
    f.persist(path).map_err(|e| e.error)?;
    Ok(())
}
fn config(root: &Path) -> Value {
    json!({"db_folder":root.join("db"),"cache_folder":root.join("cache"),"number_of_eps_per_fp":2,"filter_size_time":20,"min_match_count":3,"max_results":50,"max_db_collisions":2000,"skip_saturated_hashes":true,"independent_time_votes":false,"skip_duplicates":false,"allowed_audio_file_extensions":AUDIO.split_whitespace().map(|e|format!(".{e}")).collect::<Vec<_>>()})
}

pub struct Backend {
    root: PathBuf,
    exe: PathBuf,
    manifest: Manifest,
    _lock: File,
}
impl Backend {
    pub fn open(root: &Path, source: &Path, create: bool) -> Result<Self> {
        if !root.exists() && !create {
            bail!("No Olaf index yet. Index a music folder first. Rust remains available with --backend rust.");
        }
        if root.exists() && !root.is_dir() {
            bail!("Olaf needs its own directory, not a Rust database file");
        }
        fs::create_dir_all(root)?;
        let root = index::normalize(root)?;
        // JSON configuration and Olaf's file-list protocol require Unicode paths.
        // Fail explicitly instead of panicking in serde_json or aliasing lossy paths.
        root.to_str()
            .context("Olaf index directory must be valid Unicode")?;
        let lock = File::options()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(root.join("app.lock"))?;
        lock.try_lock()
            .context("Another app operation is using this Olaf index")?;
        let marker = root.join("index-version.json");
        let runtime = root.join("runtime");
        let exe = runtime.join(runtime_name());
        if root.join("home/.olaf/olaf_config.json").exists() {
            bail!("Unexpected home configuration override in isolated Olaf runtime");
        }
        let manifest = if marker.exists() {
            let m: Manifest = serde_json::from_reader(BufReader::new(File::open(&marker)?))?;
            if m.version != VERSION {
                bail!("Incompatible Olaf index version. Use a new --olaf-index directory and rebuild; the old index is preserved.");
            }
            if digest(&exe).with_context(|| format!("Cannot read the index's pinned Olaf runtime: {}. Runtimes are target-specific; use a new --olaf-index directory when changing targets, not an in-place runtime replacement.", exe.display()))? != m.binary_sha256 {
                bail!("Olaf executable changed. Rebuild in a new index directory.");
            }
            check_executable(&exe)?;
            let saved: Value = serde_json::from_reader(BufReader::new(File::open(
                runtime.join("olaf_config.json"),
            )?))?;
            if saved != config(&root) {
                bail!("Olaf configuration differs from the index version. Restore it or rebuild separately.");
            }
            m
        } else {
            if !create {
                bail!("Missing index version manifest; refusing an unversioned index");
            }
            if root.join("db").exists() {
                bail!("Unversioned database found; refusing to adopt or overwrite it");
            }
            if !source.is_file() {
                bail!(
                    "Olaf runtime missing: {}. Use a release package containing olaf-runtime/{} beside local-shazam{}. For source builds, run cargo build --locked --release --manifest-path rust-app/Cargo.toml, place the application at the package root, and separately build the matching patched Olaf source for this target into olaf-runtime/{}. Use --olaf-bin PATH to seed a new index from that runtime; existing indexes are not upgraded.",
                    source.display(), runtime_name(), if cfg!(windows) { ".exe" } else { "" }, runtime_name()
                );
            }
            check_executable(source)?;
            fs::create_dir_all(&runtime)?;
            fs::copy(source, &exe)?;
            check_executable(&exe)?;
            atomic_json(&runtime.join("olaf_config.json"), &config(&root))?;
            let m = Manifest {
                version: VERSION.into(),
                binary_sha256: digest(&exe)?,
                files: BTreeMap::new(),
            };
            atomic_json(&marker, &m)?;
            m
        };
        for dir in ["temp", "home", "cache"] {
            fs::create_dir_all(root.join(dir))?;
        }
        Ok(Self {
            root,
            exe,
            manifest,
            _lock: lock,
        })
    }
    fn command(&self, action: &str) -> Command {
        let mut c = audio::command(&self.exe);
        c.arg(action)
            .current_dir(&self.root)
            .env("HOME", self.root.join("home"))
            .env("USERPROFILE", self.root.join("home"));
        c
    }
    fn save(&self) -> Result<()> {
        atomic_json(&self.root.join("index-version.json"), &self.manifest)
    }
    fn batch(
        &mut self,
        jobs: &[(PathBuf, String)],
        workers: u16,
        report: &mut index::Report,
    ) -> Result<()> {
        if jobs.is_empty() {
            return Ok(());
        }
        let mut cmd = self.command("store");
        cmd.args([
            "--force",
            "--format",
            "json",
            "--threads",
            &workers.to_string(),
        ]);
        // A bounded file list bypasses Windows' command-line length limit.
        let mut list = tempfile::Builder::new()
            .suffix(".txt")
            .tempfile_in(self.root.join("temp"))?;
        for (path, _) in jobs {
            let path = path.to_str().context("Audio path is not valid Unicode")?;
            if path.contains(['\n', '\r']) {
                bail!("Newlines in audio paths are unsupported by Olaf's list protocol");
            }
            writeln!(list, "{path}")?;
        }
        list.flush()?;
        cmd.arg(list.path());
        match execute_output(cmd, 1800, &self.root.join("temp")) {
            Ok((_, stderr, success)) => {
                if !success || stderr.contains("Warning:") {
                    let mut log = File::options()
                        .create(true)
                        .append(true)
                        .open(self.root.join("index-errors.log"))?;
                    writeln!(log, "\n--- index batch: {} files ---\n{stderr}", jobs.len())?;
                }
                record_stores(jobs, &stderr, &mut self.manifest, report);
                // Commit confirmed successes even after a nonzero child exit.
                self.save()?;
            }
            Err(e) => {
                let detail = format!("Batch operation failed: {e:#}");
                eprintln!("{detail}");
                for (path, _) in jobs {
                    report.failed += 1;
                    report.errors.push(index::Failure {
                        filepath: path.clone(),
                        error: detail.clone(),
                    });
                }
            }
        }
        Ok(())
    }
    pub fn bootstrap(
        &mut self,
        dirs: &[PathBuf],
        workers: u16,
        force: bool,
        progress: bool,
    ) -> Result<index::Report> {
        if !(1..=64).contains(&workers) {
            bail!("workers must be between 1 and 64");
        }
        let batch_size = batch_size(workers);
        if progress {
            eprintln!("Indexing with {workers} workers; bounded queue {batch_size}. Completed batches are saved for resume.");
        }
        let start = Instant::now();
        let mut report = index::Report::default();
        let mut jobs = Vec::new();
        let mut seen = BTreeSet::new();
        let index_root = self.root.clone();
        for dir in dirs {
            if !dir.is_dir() {
                bail!("Not a directory: {}", dir.display());
            }
            for entry in walkdir::WalkDir::new(dir)
                .follow_links(false)
                .into_iter()
                .filter_entry(|e| {
                    !e.file_type().is_dir()
                        || (!matches!(
                            e.file_name().to_str(),
                            Some(".git" | ".venv" | "target" | "__pycache__")
                        ) && index::normalize(e.path()).map_or(true, |p| p != index_root))
                })
            {
                let entry = entry?;
                if !entry.file_type().is_file() {
                    continue;
                }
                let ext = entry
                    .path()
                    .extension()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .to_lowercase();
                if !AUDIO.split_whitespace().any(|x| x == ext) {
                    report.ignored += 1;
                    continue;
                }
                let path = index::normalize(entry.path())?;
                if !seen.insert(path.clone()) {
                    continue;
                }
                report.total += 1;
                let id = match index::identity(&path, 5) {
                    Ok(id) => id,
                    Err(e) => {
                        report.failed += 1;
                        report.errors.push(index::Failure {
                            filepath: path,
                            error: format!("{e:#}"),
                        });
                        continue;
                    }
                };
                if !force && self.manifest.files.get(path.to_string_lossy().as_ref()) == Some(&id) {
                    report.skipped += 1;
                    continue;
                }
                jobs.push((path, id));
                if jobs.len() == batch_size {
                    self.batch(&jobs, workers, &mut report)?;
                    jobs.clear();
                    if progress {
                        eprintln!(
                            "Indexed {}, skipped {}, failed {}",
                            report.indexed, report.skipped, report.failed
                        );
                    }
                }
            }
        }
        self.batch(&jobs, workers, &mut report)?;
        report.seconds = start.elapsed().as_secs_f64();
        Ok(report)
    }
    pub fn status(&self) -> Value {
        json!({"backend":"olaf","index_version":VERSION,"policy":POLICY,"songs":self.manifest.files.len(),"bytes":self.root.join("db/data.mdb").metadata().map(|m|m.len()).unwrap_or(0),"directory":self.root})
    }
    pub fn recognize(&self, snippet: &Path, top: usize) -> Result<Recognition> {
        if self.manifest.files.is_empty() {
            bail!("Olaf index is empty; index a folder first");
        }
        let temp = tempfile::tempdir_in(self.root.join("temp"))?;
        // Decode once into a bounded 30-second query; the same audio feeds both engines.
        let pcm = decode(snippet, 0., MAX_QUERY, temp.path())?;
        let duration = pcm.len() as f64 / RATE as f64;
        let query = temp.path().join("query.wav");
        write_wav(&query, &pcm)?;
        let mut cmd = self.command("query");
        cmd.args(["--format", "json"]).arg(&query);
        let (bytes, stderr) = execute(cmd, 120, temp.path())?;
        let obj: Value = serde_json::from_slice(&bytes)?;
        let mut raw: Vec<RawMatch> = serde_json::from_value(obj["matches"].clone())?;
        raw.retain(|m| {
            m.match_count >= 3
                && m.query_start.is_finite()
                && m.query_stop.is_finite()
                && m.reference_start.is_finite()
                && m.query_stop - m.query_start >= 0.15
        });
        raw.sort_by(|a, b| b.match_count.cmp(&a.match_count).then(a.path.cmp(&b.path)));
        let mut seen = BTreeSet::new();
        raw.retain(|m| seen.insert(candidate_key(&m.path)));
        let mut warnings=vec!["Experimental evidence thresholds; labels are not probabilities. At most the first 30 seconds are analyzed.".into()];
        let shortlist_truncated = raw.len() > 10;
        raw.truncate(10);
        if shortlist_truncated {
            warnings.push(
                "Candidate shortlist limited to ten distinct files; no strong-match designation."
                    .into(),
            );
        }
        if stderr.contains("Results full") {
            warnings.push("Common fingerprint lookups reached the retrieval cap.".into());
        }
        let qfp = prints(&pcm)?;
        let mut verified = Vec::new();
        let mut errors = false;
        for m in raw {
            // Only accept paths registered by this application; never follow arbitrary output.
            if !self.manifest.files.contains_key(&m.path) {
                errors = true;
                warnings.push(format!("Unregistered candidate omitted: {}", m.path));
                continue;
            }
            let result = (|| -> Result<Option<Candidate>> {
                if index::identity(Path::new(&m.path), 5)? != self.manifest.files[&m.path] {
                    bail!("file changed since indexing; reindex its folder");
                }
                let offset = m.reference_start - m.query_start;
                if offset < -0.5 {
                    return Ok(None);
                }
                let start = (offset - 1.).max(0.);
                let reference = decode(Path::new(&m.path), start, duration + 2., temp.path())?;
                let rfp = prints(&reference)?;
                let evidence = verify(&qfp, &rfp, offset - start);
                if evidence.0 < 4 || evidence.1 < 4 || evidence.2 < 0.4 {
                    return Ok(None);
                }
                Ok(Some(Candidate {
                    path: m.path.clone(),
                    offset_seconds: start + evidence.3,
                    label: "tentative".into(),
                    anchors: evidence.0,
                    distinct_hashes: evidence.1,
                    evidence_span_seconds: evidence.2,
                    olaf_votes: m.match_count,
                }))
            })();
            match result {
                Ok(Some(c)) => verified.push(c),
                Ok(None) => (),
                Err(e) => {
                    errors = true;
                    warnings.push(format!("Could not verify {}: {e:#}", m.path));
                }
            }
        }
        let strong = classify(&mut verified, duration, errors || shortlist_truncated);
        verified.truncate(top.clamp(1, 3));
        let status = if strong {
            "strong_match"
        } else if verified.is_empty() {
            "insufficient_evidence"
        } else {
            "possible_matches"
        };
        Ok(Recognition {
            snippet: snippet.into(),
            status: status.into(),
            analyzed_seconds: duration,
            policy: POLICY,
            matches: verified,
            warnings,
        })
    }
}
fn successful_stores(stderr: &str) -> BTreeSet<String> {
    stderr
        .lines()
        .filter_map(|line| serde_json::from_str::<Value>(line).ok())
        .filter(|r| r["action"] == "store")
        .filter_map(|r| r["audio_identifier"].as_str().map(str::to_owned))
        .collect()
}
// Called regardless of the subprocess exit status: only per-file records confirm success.
fn record_stores(
    jobs: &[(PathBuf, String)],
    stderr: &str,
    manifest: &mut Manifest,
    report: &mut index::Report,
) {
    let completed = successful_stores(stderr);
    for (path, id) in jobs {
        if completed.contains(path.to_string_lossy().as_ref()) {
            manifest
                .files
                .insert(path.to_string_lossy().into(), id.clone());
            report.indexed += 1;
        } else {
            report.failed += 1;
            let reason = stderr
                .lines()
                .find(|line| {
                    line.contains("Failed to process")
                        && line.contains(path.to_string_lossy().as_ref())
                })
                .unwrap_or(
                    "No successful store record. See index-errors.log for batch diagnostics.",
                );
            let reason: String = reason.chars().take(2048).collect();
            eprintln!("Failed: {}: {}", path.display(), reason);
            report.errors.push(index::Failure {
                filepath: path.clone(),
                error: reason,
            });
        }
    }
}
fn classify(candidates: &mut [Candidate], duration: f64, incomplete: bool) -> bool {
    candidates.sort_by(|a, b| {
        b.anchors
            .cmp(&a.anchors)
            .then(b.distinct_hashes.cmp(&a.distinct_hashes))
            .then(a.path.cmp(&b.path))
    });
    let runner = candidates.get(1).map_or(3, |c| c.anchors);
    let strong = candidates.first().is_some_and(|c| {
        !incomplete
            && c.anchors >= 10
            && c.distinct_hashes >= 6
            && c.olaf_votes >= 6
            && c.evidence_span_seconds >= 0.8_f64.max(duration * 0.25)
            && c.anchors as f64 >= runner as f64 * 1.5
    });
    if strong {
        candidates[0].label = "strong".into();
    }
    strong
}
fn prints(pcm: &[f32]) -> Result<Vec<Landmark>> {
    let mut s = Stream::new(5)?;
    s.push(pcm);
    Ok(s.finish().0)
}
// Score independent query times in a narrow alignment neighborhood. Common hashes
// are ignored, each timestamp counts once, and unrelated offset buckets cannot sum.
fn verify(query: &[Landmark], reference: &[Landmark], expected: f64) -> (usize, usize, f64, f64) {
    let mut refs: HashMap<u32, Vec<u64>> = HashMap::new();
    for h in reference {
        refs.entry(h.hash).or_default().push(h.offset);
    }
    let mut bins: HashMap<i64, (BTreeSet<u64>, BTreeSet<u32>)> = HashMap::new();
    let step = HOP as f64 / RATE as f64;
    for q in query {
        if let Some(offsets) = refs.get(&q.hash) {
            if offsets.len() > 128 {
                continue;
            }
            for &r in offsets {
                let delta = r as i64 - q.offset as i64;
                if (delta as f64 * step - expected).abs() > 0.25 {
                    continue;
                }
                for bin in [delta - 1, delta, delta + 1] {
                    let entry = bins.entry(bin).or_default();
                    entry.0.insert(q.offset);
                    entry.1.insert(q.hash);
                }
            }
        }
    }
    bins.into_iter()
        .max_by(|a, b| {
            a.1 .0
                .len()
                .cmp(&b.1 .0.len())
                .then(a.1 .1.len().cmp(&b.1 .1.len()))
                .then_with(|| b.0.cmp(&a.0))
        })
        .map_or((0, 0, 0., 0.), |(delta, (anchors, hashes))| {
            let span = (anchors.last().unwrap() - anchors.first().unwrap()) as f64 * step;
            (anchors.len(), hashes.len(), span, delta as f64 * step)
        })
}
fn decode(path: &Path, start: f64, length: f64, temp: &Path) -> Result<Vec<f32>> {
    let mut cmd = audio::command("ffmpeg");
    cmd.args([
        "-nostdin",
        "-v",
        "error",
        "-threads",
        "1",
        "-ss",
        &start.to_string(),
        "-i",
    ])
    .arg(path)
    .args([
        "-t",
        &length.to_string(),
        "-map",
        "0:a:0",
        "-vn",
        "-f",
        "f32le",
        "-ac",
        "1",
        "-ar",
        "11025",
        "pipe:1",
    ]);
    let (bytes, _) = execute(cmd, 60, temp)?;
    if bytes.is_empty() || bytes.len() % 4 != 0 {
        bail!("No complete audio samples decoded");
    }
    Ok(bytes
        .as_chunks::<4>()
        .0
        .iter()
        .map(|b| f32::from_le_bytes(*b))
        .collect())
}
fn write_wav(path: &Path, pcm: &[f32]) -> Result<()> {
    let mut f = File::create(path)?;
    let bytes = (pcm.len() * 2) as u32;
    f.write_all(b"RIFF")?;
    f.write_all(&(36 + bytes).to_le_bytes())?;
    f.write_all(b"WAVEfmt ")?;
    f.write_all(&16u32.to_le_bytes())?;
    f.write_all(&1u16.to_le_bytes())?;
    f.write_all(&1u16.to_le_bytes())?;
    f.write_all(&(RATE as u32).to_le_bytes())?;
    f.write_all(&(RATE as u32 * 2).to_le_bytes())?;
    f.write_all(&2u16.to_le_bytes())?;
    f.write_all(&16u16.to_le_bytes())?;
    f.write_all(b"data")?;
    f.write_all(&bytes.to_le_bytes())?;
    for &x in pcm {
        f.write_all(&((x.clamp(-1., 1.) * 32767.) as i16).to_le_bytes())?;
    }
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    // Deliberately not a runnable binary. These tests never spawn an engine or decode audio.
    fn runtime_fixture(dir: &Path) -> PathBuf {
        let source = dir.join(runtime_name());
        fs::write(&source, b"non-audio runtime fixture").unwrap();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(&source, fs::Permissions::from_mode(0o755)).unwrap();
        }
        source
    }
    #[test]
    fn bounded_batches_scale_without_unbounded_queues() {
        assert_eq!(batch_size(1), 32);
        assert_eq!(batch_size(6), 96);
        assert_eq!(batch_size(64), 512);
        for workers in 1..=64 {
            assert!((32..=512).contains(&batch_size(workers)));
        }
    }
    #[test]
    fn candidate_paths_respect_platform_case_rules() {
        assert_eq!(
            candidate_key("Artist/Song.wav") == candidate_key("Artist/song.wav"),
            cfg!(windows)
        );
    }
    #[test]
    fn runtime_copy_config_and_private_home_are_pinned() {
        let dir = tempfile::tempdir().unwrap();
        let source = runtime_fixture(dir.path());
        let root = dir.path().join("index with spaces 音楽");
        let engine = Backend::open(&root, &source, true).unwrap();
        assert_eq!(digest(&source).unwrap(), engine.manifest.binary_sha256);
        assert_eq!(engine.exe, engine.root.join("runtime").join(runtime_name()));
        let saved: Value = serde_json::from_reader(
            File::open(engine.root.join("runtime/olaf_config.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(saved, config(&engine.root));
        assert_eq!(saved["number_of_eps_per_fp"], 2);
        assert_eq!(saved["filter_size_time"], 20);
        assert_eq!(saved["skip_saturated_hashes"], true);
        assert_eq!(saved["independent_time_votes"], false);
        assert_eq!(
            engine.manifest.version,
            "olaf-local-app-v1-twopeak-time20-verifier1"
        );
        assert_eq!(POLICY, "candidate-window-v1-experimental");
        assert_eq!(MAX_QUERY, 30.0);
        let command = engine.command("store");
        assert_eq!(command.get_program(), engine.exe.as_os_str());
        assert_eq!(command.get_current_dir(), Some(engine.root.as_path()));
        assert_eq!(
            command.get_args().collect::<Vec<_>>(),
            vec![std::ffi::OsStr::new("store")]
        );
        for key in ["HOME", "USERPROFILE"] {
            let value = command
                .get_envs()
                .find(|(k, _)| *k == std::ffi::OsStr::new(key))
                .unwrap()
                .1;
            assert_eq!(value, Some(engine.root.join("home").as_os_str()));
        }
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(
                engine.exe.metadata().unwrap().permissions().mode() & 0o777,
                0o755
            );
        }
        drop(engine);
        fs::remove_file(&source).unwrap();
        // Existing indexes use their pinned runtime, not a new --olaf-bin seed.
        assert!(Backend::open(&root, &source, false).is_ok());
    }
    #[test]
    fn changed_runtime_is_rejected_not_silently_upgraded() {
        let dir = tempfile::tempdir().unwrap();
        let source = runtime_fixture(dir.path());
        let root = dir.path().join("index");
        let engine = Backend::open(&root, &source, true).unwrap();
        fs::write(&engine.exe, b"changed runtime").unwrap();
        drop(engine);
        let marker = fs::read(root.join("index-version.json")).unwrap();
        let error = Backend::open(&root, &source, true)
            .err()
            .unwrap()
            .to_string();
        assert!(error.contains("executable changed"));
        assert_eq!(fs::read(root.join("index-version.json")).unwrap(), marker);
        assert_eq!(
            fs::read(root.join("runtime").join(runtime_name())).unwrap(),
            b"changed runtime"
        );
    }
    #[test]
    fn changed_config_is_rejected_without_overwriting_it() {
        let dir = tempfile::tempdir().unwrap();
        let source = runtime_fixture(dir.path());
        let root = dir.path().join("index");
        drop(Backend::open(&root, &source, true).unwrap());
        let config_path = root.join("runtime/olaf_config.json");
        let altered = json!({"number_of_eps_per_fp":3});
        atomic_json(&config_path, &altered).unwrap();
        let error = Backend::open(&root, &source, true)
            .err()
            .unwrap()
            .to_string();
        assert!(error.contains("configuration differs"));
        assert_eq!(
            serde_json::from_reader::<_, Value>(File::open(config_path).unwrap()).unwrap(),
            altered
        );
    }
    #[test]
    fn home_override_is_rejected_before_initialization() {
        let dir = tempfile::tempdir().unwrap();
        let source = runtime_fixture(dir.path());
        let root = dir.path().join("index");
        fs::create_dir_all(root.join("home/.olaf")).unwrap();
        fs::write(root.join("home/.olaf/olaf_config.json"), b"{}").unwrap();
        let error = Backend::open(&root, &source, true)
            .err()
            .unwrap()
            .to_string();
        assert!(error.contains("home configuration override"));
        assert!(!root.join("index-version.json").exists());
        assert!(!root.join("runtime").exists());
    }
    #[test]
    fn concurrent_index_open_is_rejected() {
        let dir = tempfile::tempdir().unwrap();
        let source = runtime_fixture(dir.path());
        let root = dir.path().join("index");
        let engine = Backend::open(&root, &source, true).unwrap();
        let error = Backend::open(&root, &source, false)
            .err()
            .unwrap()
            .to_string();
        assert!(error.contains("Another app operation"));
        drop(engine);
        assert!(Backend::open(&root, &source, false).is_ok());
    }
    #[test]
    fn unversioned_database_is_never_adopted() {
        let dir = tempfile::tempdir().unwrap();
        let source = runtime_fixture(dir.path());
        let root = dir.path().join("index");
        fs::create_dir_all(root.join("db")).unwrap();
        fs::write(root.join("db/data.mdb"), b"untouched").unwrap();
        assert!(Backend::open(&root, &source, true).is_err());
        assert_eq!(fs::read(root.join("db/data.mdb")).unwrap(), b"untouched");
        assert!(!root.join("index-version.json").exists());
        assert!(!root.join("runtime").exists());
    }
    #[test]
    fn missing_index_and_database_file_are_not_created_or_converted() {
        let dir = tempfile::tempdir().unwrap();
        let missing = dir.path().join("missing");
        assert!(Backend::open(&missing, &missing, false).is_err());
        assert!(!missing.exists());
        let db = dir.path().join("legacy.db");
        fs::write(&db, b"untouched").unwrap();
        assert!(Backend::open(&db, &missing, true).is_err());
        assert_eq!(fs::read(db).unwrap(), b"untouched");
    }
    #[test]
    fn missing_runtime_explains_release_layout_and_override() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path().join("index");
        let error = Backend::open(&root, &dir.path().join("missing"), true)
            .err()
            .unwrap()
            .to_string();
        assert!(error.contains("olaf-runtime/"));
        assert!(error.contains("cargo build --locked --release"));
        assert!(error.contains("--olaf-bin PATH"));
        assert!(!error.contains("Build-Rust.ps1"));
        assert!(!root.join("index-version.json").exists());
    }
    #[test]
    fn olaf_worker_bounds_fail_before_scanning_or_starting_a_runtime() {
        let dir = tempfile::tempdir().unwrap();
        let source = runtime_fixture(dir.path());
        let root = dir.path().join("index");
        let mut engine = Backend::open(&root, &source, true).unwrap();
        for workers in [0, 65, u16::MAX] {
            let error = engine
                .bootstrap(&[dir.path().join("missing")], workers, false, false)
                .unwrap_err()
                .to_string();
            assert!(error.contains("workers must be between 1 and 64"));
        }
        assert!(engine.manifest.files.is_empty());
    }
    #[cfg(unix)]
    #[test]
    fn missing_execute_permission_is_actionable() {
        use std::os::unix::fs::PermissionsExt;
        let dir = tempfile::tempdir().unwrap();
        let source = runtime_fixture(dir.path());
        fs::set_permissions(&source, fs::Permissions::from_mode(0o644)).unwrap();
        let root = dir.path().join("index");
        let error = Backend::open(&root, &source, true)
            .err()
            .unwrap()
            .to_string();
        assert!(error.contains("chmod +x"));
        assert!(!root.join("index-version.json").exists());
    }
    #[cfg(unix)]
    #[test]
    fn non_unicode_index_path_returns_error_instead_of_panicking() {
        use std::{ffi::OsString, os::unix::ffi::OsStringExt};
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path().join(OsString::from_vec(b"index-\xff".to_vec()));
        let error = Backend::open(&root, Path::new("missing"), true)
            .err()
            .unwrap()
            .to_string();
        assert!(error.contains("valid Unicode"));
        assert!(!root.join("index-version.json").exists());
    }
    #[test]
    fn mixed_batch_preserves_successful_records() {
        let log = "{\"action\":\"store\",\"audio_identifier\":\"good.wav\"}\nerror: Failed to process bad.wav: DecodeFailed\n{\"action\":\"skip\",\"audio_identifier\":\"other.wav\"}\n";
        let done = successful_stores(log);
        assert_eq!(done, BTreeSet::from(["good.wav".to_string()]));
        let mut manifest = Manifest {
            version: VERSION.into(),
            binary_sha256: String::new(),
            files: BTreeMap::new(),
        };
        let jobs = [
            (PathBuf::from("good.wav"), "good-id".into()),
            (PathBuf::from("bad.wav"), "bad-id".into()),
        ];
        let mut report = index::Report::default();
        record_stores(&jobs, log, &mut manifest, &mut report);
        assert_eq!(report.indexed, 1);
        assert_eq!(report.failed, 1);
        assert_eq!(manifest.files.get("good.wav").unwrap(), "good-id");
        assert!(!manifest.files.contains_key("bad.wav"));
        assert_eq!(report.errors.len(), 1);
        assert_eq!(report.errors[0].filepath, Path::new("bad.wav"));
    }
    #[test]
    fn atomic_manifest_roundtrip() {
        let dir = tempfile::tempdir().unwrap();
        let p = dir.path().join("manifest.json");
        atomic_json(&p, &json!({"a":1})).unwrap();
        atomic_json(&p, &json!({"a":2})).unwrap();
        assert_eq!(
            serde_json::from_reader::<_, Value>(File::open(p).unwrap()).unwrap(),
            json!({"a":2})
        );
    }
    #[test]
    fn repeated_pairs_are_not_independent_evidence() {
        let q = vec![
            Landmark {
                hash: 1,
                offset: 10
            };
            100
        ];
        let r = vec![
            Landmark {
                hash: 1,
                offset: 30
            };
            100
        ];
        let e = verify(&q, &r, 20. * HOP as f64 / RATE as f64);
        assert_eq!(e.0, 1);
        assert_eq!(e.1, 1);
        assert_eq!(e.2, 0.);
    }
    #[test]
    fn unrelated_offsets_do_not_verify() {
        let q = vec![Landmark {
            hash: 1,
            offset: 10,
        }];
        let r = vec![Landmark {
            hash: 1,
            offset: 300,
        }];
        assert_eq!(verify(&q, &r, 0.).0, 0);
    }
    #[test]
    fn aligned_distinct_anchors_verify() {
        let q: Vec<_> = (0..20)
            .map(|i| Landmark {
                hash: i,
                offset: i as u64 * 3,
            })
            .collect();
        let r: Vec<_> = q
            .iter()
            .map(|h| Landmark {
                hash: h.hash,
                offset: h.offset + 20,
            })
            .collect();
        let e = verify(&q, &r, 20. * HOP as f64 / RATE as f64);
        assert_eq!(e.0, 20);
        assert_eq!(e.1, 20);
        assert!(e.2 > 2.);
    }
    #[test]
    fn ambiguity_and_incomplete_checks_block_strong() {
        let c = Candidate {
            path: "one".into(),
            offset_seconds: 0.,
            label: "tentative".into(),
            anchors: 20,
            distinct_hashes: 15,
            evidence_span_seconds: 4.,
            olaf_votes: 30,
        };
        assert!(classify(&mut [c.clone()], 10., false));
        assert!(!classify(&mut [c.clone()], 10., true));
        assert!(!classify(&mut [c.clone(), c], 10., false));
    }
    #[test]
    fn mismatched_index_version_is_rejected() {
        let d = tempfile::tempdir().unwrap();
        atomic_json(
            &d.path().join("index-version.json"),
            &Manifest {
                version: "bad".into(),
                binary_sha256: "".into(),
                files: BTreeMap::new(),
            },
        )
        .unwrap();
        assert!(Backend::open(d.path(), Path::new("missing"), false).is_err());
    }
}
