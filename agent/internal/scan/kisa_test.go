//go:build linux

package scan

import (
	"os"
	"strings"
	"testing"
)

func TestEvalPerm(t *testing.T) {
	cases := []struct {
		name    string
		mode    os.FileMode
		uid     uint32
		maxPerm os.FileMode
		want    bool
	}{
		{"passwd 644 root ok", 0o644, 0, 0o644, true},
		{"passwd 640 root subset ok", 0o640, 0, 0o644, true},
		{"passwd 664 group-write fail", 0o664, 0, 0o644, false},
		{"passwd 646 other-write fail", 0o646, 0, 0o644, false},
		{"passwd 644 non-root fail", 0o644, 1000, 0o644, false},
		{"shadow 640 root ok", 0o640, 0, 0o640, true},
		{"shadow 644 group+other-read fail", 0o644, 0, 0o640, false},
		{"shadow 600 root subset ok", 0o600, 0, 0o640, true},
	}
	for _, c := range cases {
		if got := evalPerm(c.mode, c.uid, c.maxPerm); got != c.want {
			t.Errorf("%s: evalPerm(%o,%d,%o)=%v want %v", c.name, c.mode, c.uid, c.maxPerm, got, c.want)
		}
	}
}

func TestParseLastDirective(t *testing.T) {
	conf := "# comment\nPermitRootLogin yes\nPort 22\nPermitRootLogin no\n"
	v, ok := parseLastDirective(strings.NewReader(conf), "PermitRootLogin")
	if !ok || v != "no" {
		t.Errorf("got %q,%v want no,true (last wins)", v, ok)
	}
	if _, ok := parseLastDirective(strings.NewReader(conf), "Absent"); ok {
		t.Error("absent directive should report not found")
	}
}

func TestParseUID0(t *testing.T) {
	passwd := "root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1::/usr/sbin:/usr/sbin/nologin\nbackdoor:x:0:0::/:/bin/bash\n"
	names := parseUID0(strings.NewReader(passwd))
	if len(names) != 2 || names[0] != "root" || names[1] != "backdoor" {
		t.Errorf("got %v want [root backdoor]", names)
	}
}

func TestParseTMOUT(t *testing.T) {
	if v, ok := parseTMOUT(strings.NewReader("export TMOUT=600\n")); !ok || v != 600 {
		t.Errorf("export form: got %d,%v want 600,true", v, ok)
	}
	if v, ok := parseTMOUT(strings.NewReader("TMOUT=300 ; readonly TMOUT\n")); !ok || v != 300 {
		t.Errorf("trailing form: got %d,%v want 300,true", v, ok)
	}
	if _, ok := parseTMOUT(strings.NewReader("# TMOUT=600\nPATH=/bin\n")); ok {
		t.Error("commented/absent TMOUT should report not found")
	}
}

func TestCollectKISAReturnsFindings(t *testing.T) {
	// 실행 환경의 실제 /etc 상태에 따라 pass/fail은 달라지지만, 구현된 항목 수만큼
	// 각각 하나의 finding이 Tool "kisa"로 생성되어야 한다.
	findings := CollectKISA()
	if len(findings) != 10 {
		t.Fatalf("expected 10 KISA findings, got %d", len(findings))
	}
	for _, f := range findings {
		if f.Tool != "kisa" || f.CheckID == "" {
			t.Errorf("malformed finding: %+v", f)
		}
	}
}
