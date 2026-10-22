package collector

import "testing"

func TestParseFileList(t *testing.T) {
	out := "/etc/nginx\n/etc/nginx/nginx.conf\n/var/log/nginx\n\n"
	got := parseFileList(out)
	if len(got) != 3 {
		t.Fatalf("expected 3 files, got %d (%v)", len(got), got)
	}
	if got[1] != "/etc/nginx/nginx.conf" {
		t.Fatalf("unexpected file: %q", got[1])
	}
}

func TestParseFileListNoFiles(t *testing.T) {
	if got := parseFileList("(contains no files)\n"); len(got) != 0 {
		t.Fatalf("expected empty, got %v", got)
	}
}
