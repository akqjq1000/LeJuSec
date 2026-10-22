package fim

import (
	"os"
	"path/filepath"
	"testing"
)

func TestScanAndChangeDetection(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "a.conf")
	if err := os.WriteFile(path, []byte("hello"), 0o644); err != nil {
		t.Fatal(err)
	}

	m1 := Scan([]string{path})
	if len(m1.Files) != 1 || m1.Files[0].SHA256 == "" {
		t.Fatalf("unexpected manifest: %+v", m1)
	}
	if m1.AgentSHA256 == "" {
		t.Fatal("expected agent self hash to be set")
	}

	if err := os.WriteFile(path, []byte("changed"), 0o644); err != nil {
		t.Fatal(err)
	}
	m2 := Scan([]string{path})
	if m1.Files[0].SHA256 == m2.Files[0].SHA256 {
		t.Fatal("hash should change after file modification")
	}
}

func TestScanDirAndMissing(t *testing.T) {
	dir := t.TempDir()
	for _, name := range []string{"x", "y"} {
		if err := os.WriteFile(filepath.Join(dir, name), []byte(name), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	m := Scan([]string{dir, "/no/such/path/here"})
	if len(m.Files) != 2 {
		t.Fatalf("want 2 files, got %d", len(m.Files))
	}
}
