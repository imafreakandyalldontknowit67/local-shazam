"""Source-level menu presentation/dispatch checks, not runtime validation.

Reads only rust-app/src/main.rs using the Python standard library. No app,
subprocess, toolchain, dialogs, indexes or audio are accessed.
"""
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]


def compact(source):
    """Ignore formatting whitespace for source-level dispatch assertions."""
    return re.sub(r"\s+", "", source)


def printed_lines(source):
    """Read the menu's ordinary string literals, without executing Rust."""
    literals = re.findall(r'\bprint(?:ln)?!\s*\(\s*("(?:\\.|[^"\\])*")', source)
    return [line.strip() for literal in literals
            for line in json.loads(literal).splitlines() if line.strip()]


class MenuPresentationSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / "rust-app/src/main.rs").read_text(encoding="utf-8")
        # Bound all checks to menu(); status/results and documentation are unrelated.
        menu = re.search(r"\bfn\s+menu\b.*?(?=\bfn\s+main\b)", source, re.S)
        if menu is None:
            raise AssertionError("Could not locate menu() before main()")
        cls.signature, cls.body = menu.group(0).split("{", 1)
        cls.startup, cls.loop = re.split(r"\bloop\s*\{", cls.body, maxsplit=1)
        cls.prompt = re.split(r"\bio\s*::\s*stdout\b", cls.loop, maxsplit=1)[0]
        cls.numbered_arms = re.findall(
            r'"([1-4])"\s*=>\s*(.*?)(?=\s*"[1-4]"\s*=>|\s*_\s*=>)',
            cls.loop, re.S,
        )
        cls.arms = dict(cls.numbered_arms)

    def test_clean_title_and_friendly_numbered_labels(self):
        self.assertEqual(printed_lines(self.startup), ["Local Shazam"])
        self.assertEqual(printed_lines(self.prompt), [
            "[1] Add a music folder",
            "[2] Identify audio clips",
            "[3] View library stats",
            "[4] Exit",
            "Choose an option:",
        ])

    def test_startup_has_no_backend_path_or_experimental_diagnostics(self):
        presentation = self.startup + self.prompt
        self.assertNotRegex(presentation, r"\b(?:backend|db|olaf_index|olaf_bin)\b")
        self.assertNotRegex(presentation, r"\.\s*display\s*\(")
        self.assertNotRegex(presentation.lower(), r"index:|experimental|guaranteed|\{:\?\}")

    def test_signature_and_numbered_mapping_are_preserved(self):
        self.assertEqual(compact(self.signature), compact("""
            fn menu(db: &Path, backend: Backend, olaf_index: &Path,
                    olaf_bin: &Path) -> Result<()>
        """))
        self.assertEqual([key for key, _ in self.numbered_arms], ["1", "2", "3", "4"])
        self.assertIn("letaction=matchchoice.trim(){", compact(self.loop))
        self.assertEqual(compact(self.arms["3"]), "Some(Action::Status),")
        self.assertEqual(compact(self.arms["4"]), "break,")

    def test_add_folder_keeps_worker_selection_and_bootstrap_parameters(self):
        arm = compact(self.arms["1"])
        self.assertIn("ifletSome(folder)=rfd::FileDialog::new()", arm)
        self.assertIn(compact("""
            .pick_folder() {
                choose_workers()?.map(|workers| Action::Bootstrap {
                    directories: vec![folder],
                    workers,
                    compact: false,
                    force: false,
                })
            } else {
                None
            }
        """), arm)

    def test_identify_keeps_multiple_file_picker_and_top_ten(self):
        arm = compact(self.arms["2"])
        self.assertTrue(arm.startswith("rfd::FileDialog::new()"))
        self.assertIn(compact("""
            .pick_files().map(|snippets| Action::Match { snippets, top: 10 })
        """), arm)

    def test_input_flush_eof_and_invalid_option_retry_are_preserved(self):
        loop = compact(self.loop)
        self.assertIn(compact("""
            io::stdout().flush()?;
            let mut choice = String::new();
            if io::stdin().read_line(&mut choice)? == 0 {
                break;
            }
        """), loop)
        self.assertIn(compact("""
            _ => {
                println!("Invalid option.");
                continue;
            }
        """), loop)

    def test_run_arguments_error_handling_and_cancellation_are_preserved(self):
        self.assertIn(compact("""
            if let Some(action) = action {
                if let Err(e) = run(action, db, false, backend, olaf_index, olaf_bin) {
                    eprintln!("Error: {e:#}");
                }
            } else {
                println!("Cancelled.");
            }
        """), compact(self.loop))
        self.assertTrue(compact(self.body).endswith("}Ok(())}"))


if __name__ == "__main__":
    unittest.main()
