package scan

import (
	"os"
	"path/filepath"
	"testing"
)

const trivyJSON = `{"Results":[{"Target":"app","Vulnerabilities":[
  {"VulnerabilityID":"CVE-2024-0001","PkgName":"openssl","Severity":"HIGH","Title":"openssl flaw"},
  {"VulnerabilityID":"CVE-2024-0002","PkgName":"zlib","Severity":"CRITICAL"}
]}]}`

const lynisDat = `# lynis report
warning[]=SSH-7408|Harden SSH configuration|-|-
suggestion[]=AUTH-9286|Set password aging|-|-
hardening_index=60
`

const openscapXML = `<TestResult xmlns="http://checklists.nist.gov/xccdf/1.2">
  <rule-result idref="rule_sshd_disable_root_login"><result>fail</result></rule-result>
  <rule-result idref="rule_set_password_hashing"><result>pass</result></rule-result>
  <rule-result idref="rule_na"><result>notapplicable</result></rule-result>
</TestResult>`

func TestParseTrivy(t *testing.T) {
	findings, err := parseTrivy([]byte(trivyJSON))
	if err != nil {
		t.Fatal(err)
	}
	if len(findings) != 2 {
		t.Fatalf("want 2 findings, got %d", len(findings))
	}
	if findings[0].CheckID != "CVE-2024-0001" || findings[0].Severity != "high" {
		t.Fatalf("unexpected: %+v", findings[0])
	}
	if findings[0].Passed != nil {
		t.Fatal("trivy findings should have nil Passed")
	}
	if findings[1].Severity != "critical" {
		t.Fatalf("want critical, got %s", findings[1].Severity)
	}
}

func TestParseLynis(t *testing.T) {
	findings := parseLynis([]byte(lynisDat))
	if len(findings) != 2 {
		t.Fatalf("want 2, got %d", len(findings))
	}
	if findings[0].CheckID != "SSH-7408" || findings[0].Severity != "high" {
		t.Fatalf("unexpected warning: %+v", findings[0])
	}
	if findings[0].Passed == nil || *findings[0].Passed {
		t.Fatal("lynis warning should be Passed=false")
	}
	if findings[1].CheckID != "AUTH-9286" || findings[1].Severity != "low" {
		t.Fatalf("unexpected suggestion: %+v", findings[1])
	}
}

func TestParseOpenSCAP(t *testing.T) {
	findings, err := parseOpenSCAP([]byte(openscapXML))
	if err != nil {
		t.Fatal(err)
	}
	byID := map[string]*bool{}
	for _, f := range findings {
		byID[f.CheckID] = f.Passed
	}
	if p := byID["rule_sshd_disable_root_login"]; p == nil || *p {
		t.Fatal("root login rule should be Passed=false")
	}
	if p := byID["rule_set_password_hashing"]; p == nil || !*p {
		t.Fatal("hashing rule should be Passed=true")
	}
	if byID["rule_na"] != nil {
		t.Fatal("notapplicable should be Passed=nil")
	}
}

func TestCollectFromFiles(t *testing.T) {
	dir := t.TempDir()
	lynisPath := filepath.Join(dir, "lynis-report.dat")
	oscapPath := filepath.Join(dir, "results.xml")
	if err := os.WriteFile(lynisPath, []byte(lynisDat), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(oscapPath, []byte(openscapXML), 0o600); err != nil {
		t.Fatal(err)
	}

	findings, err := Collect(Config{LynisReport: lynisPath, OpenSCAPResults: oscapPath})
	if err != nil {
		t.Fatal(err)
	}
	// 2 lynis + 3 openscap
	if len(findings) != 5 {
		t.Fatalf("want 5 findings, got %d", len(findings))
	}
}

func TestCollectEmpty(t *testing.T) {
	findings, err := Collect(Config{})
	if err != nil {
		t.Fatal(err)
	}
	if len(findings) != 0 {
		t.Fatalf("want 0, got %d", len(findings))
	}
}
