package collector

import "testing"

func TestParseDpkg(t *testing.T) {
	out := "openssl\t3.0.2-0ubuntu1.18\nnginx\t1.24.0-1\n\n  \n"
	pkgs := parseDpkg(out)
	if len(pkgs) != 2 {
		t.Fatalf("expected 2 packages, got %d", len(pkgs))
	}
	if pkgs[0].Name != "openssl" || pkgs[0].Version != "3.0.2-0ubuntu1.18" {
		t.Fatalf("unexpected first package: %+v", pkgs[0])
	}
	if pkgs[1].Source != "dpkg" {
		t.Fatalf("expected source dpkg, got %q", pkgs[1].Source)
	}
}

func TestParseRPM(t *testing.T) {
	pkgs := parseRPM("httpd\t2.4.57-5.el9\n")
	if len(pkgs) != 1 || pkgs[0].Source != "rpm" || pkgs[0].Name != "httpd" {
		t.Fatalf("unexpected: %+v", pkgs)
	}
}

func TestParsePacman(t *testing.T) {
	pkgs := parsePacman("bash 5.2.021-5\nopenssl 3.3.2-1\n")
	if len(pkgs) != 2 {
		t.Fatalf("expected 2, got %d", len(pkgs))
	}
	if pkgs[1].Name != "openssl" || pkgs[1].Version != "3.3.2-1" || pkgs[1].Source != "pacman" {
		t.Fatalf("unexpected: %+v", pkgs[1])
	}
}

func TestParseEmpty(t *testing.T) {
	if got := parseDpkg(""); len(got) != 0 {
		t.Fatalf("expected empty, got %d", len(got))
	}
}
