package remediate

import (
	"errors"
	"testing"
)

// fakeRunner fails for scripts listed in failing, succeeds otherwise.
func fakeRunner(failing map[string]bool) Runner {
	return func(script string) (string, error) {
		if failing[script] {
			return "boom", errors.New("exit 1")
		}
		return "ok", nil
	}
}

func TestApplySucceeds(t *testing.T) {
	r := Apply(1, "sed -i s/a/b/ f", "cp f.bak f", fakeRunner(nil))
	if r.Status != "applied" {
		t.Fatalf("want applied, got %s (%s)", r.Status, r.Output)
	}
}

func TestApplyFailureRollsBack(t *testing.T) {
	r := Apply(2, "do-apply", "do-rollback", fakeRunner(map[string]bool{"do-apply": true}))
	if r.Status != "rolled_back" {
		t.Fatalf("want rolled_back, got %s", r.Status)
	}
}

func TestApplyAndRollbackFail(t *testing.T) {
	r := Apply(3, "do-apply", "do-rollback", fakeRunner(map[string]bool{"do-apply": true, "do-rollback": true}))
	if r.Status != "failed" {
		t.Fatalf("want failed, got %s", r.Status)
	}
}

func TestDangerousScriptSkipped(t *testing.T) {
	called := false
	run := func(string) (string, error) {
		called = true
		return "", nil
	}
	r := Apply(4, "rm -rf /", "cp f.bak f", run)
	if r.Status != "skipped" {
		t.Fatalf("want skipped, got %s", r.Status)
	}
	if called {
		t.Fatal("dangerous script must not be executed")
	}
}
