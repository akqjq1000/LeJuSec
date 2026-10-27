// Package scan runs host security scanners (Trivy/Lynis/OpenSCAP) and
// normalizes their output into findings for the control plane. Parsers are
// pure functions (tested); runners exec the tool when present. The control
// plane's rule engine decides pass/fail — the agent only reports facts.
package scan

import (
	"encoding/json"
	"encoding/xml"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
)

// Finding mirrors the control plane's normalized finding (JSON-compatible).
type Finding struct {
	Tool     string `json:"tool"`
	CheckID  string `json:"check_id"`
	Title    string `json:"title,omitempty"`
	Severity string `json:"severity,omitempty"`
	Passed   *bool  `json:"passed"`
	Target   string `json:"target,omitempty"`
	Detail   string `json:"detail,omitempty"`
}

func normSeverity(value string) string {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "critical", "high", "medium", "low", "info":
		return strings.ToLower(strings.TrimSpace(value))
	default:
		return "unknown"
	}
}

// ---- Trivy (vulnerabilities, JSON) ----

type trivyReport struct {
	Results []struct {
		Target          string `json:"Target"`
		Vulnerabilities []struct {
			VulnerabilityID string `json:"VulnerabilityID"`
			PkgName         string `json:"PkgName"`
			Severity        string `json:"Severity"`
			Title           string `json:"Title"`
		} `json:"Vulnerabilities"`
	} `json:"Results"`
}

func parseTrivy(raw []byte) ([]Finding, error) {
	var report trivyReport
	if err := json.Unmarshal(raw, &report); err != nil {
		return nil, fmt.Errorf("parse trivy json: %w", err)
	}
	findings := make([]Finding, 0)
	for _, result := range report.Results {
		for _, vuln := range result.Vulnerabilities {
			title := vuln.Title
			if title == "" {
				title = vuln.PkgName
			}
			findings = append(findings, Finding{
				Tool:     "trivy",
				CheckID:  vuln.VulnerabilityID,
				Title:    title,
				Severity: normSeverity(vuln.Severity),
				Target:   result.Target,
				Detail:   vuln.PkgName,
			})
		}
	}
	return findings, nil
}

// ---- Lynis (report .dat: warning[]=.. / suggestion[]=..) ----

func parseLynis(raw []byte) []Finding {
	kinds := []struct {
		prefix   string
		severity string
	}{{"warning[]=", "high"}, {"suggestion[]=", "low"}}

	findings := make([]Finding, 0)
	for _, rawLine := range strings.Split(string(raw), "\n") {
		text := strings.TrimSpace(rawLine)
		for _, kind := range kinds {
			if !strings.HasPrefix(text, kind.prefix) {
				continue
			}
			payload := text[len(kind.prefix):]
			parts := strings.Split(payload, "|")
			id := "unknown"
			if len(parts) > 0 && parts[0] != "" {
				id = parts[0]
			}
			title := ""
			if len(parts) > 1 {
				title = parts[1]
			}
			failed := false
			findings = append(findings, Finding{
				Tool:     "lynis",
				CheckID:  id,
				Title:    title,
				Severity: kind.severity,
				Passed:   &failed,
				Detail:   payload,
			})
		}
	}
	return findings
}

// ---- OpenSCAP (XCCDF results XML: rule-result/result) ----

func parseOpenSCAP(raw []byte) ([]Finding, error) {
	decoder := xml.NewDecoder(strings.NewReader(string(raw)))
	findings := make([]Finding, 0)
	for {
		tok, err := decoder.Token()
		if err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			return nil, fmt.Errorf("parse openscap xml: %w", err)
		}
		start, ok := tok.(xml.StartElement)
		if !ok || start.Name.Local != "rule-result" {
			continue
		}
		idref := ""
		for _, attr := range start.Attr {
			if attr.Name.Local == "idref" {
				idref = attr.Value
			}
		}
		result, err := readResultText(decoder)
		if err != nil {
			return nil, err
		}
		findings = append(findings, Finding{
			Tool:     "openscap",
			CheckID:  idref,
			Title:    idref,
			Severity: "medium",
			Passed:   resultToPassed(result),
			Detail:   result,
		})
	}
	return findings, nil
}

func resultToPassed(result string) *bool {
	switch strings.ToLower(strings.TrimSpace(result)) {
	case "pass":
		v := true
		return &v
	case "fail":
		v := false
		return &v
	default:
		return nil
	}
}

// readResultText consumes tokens up to </rule-result>, returning the text of
// the inner <result> element.
func readResultText(decoder *xml.Decoder) (string, error) {
	var result strings.Builder
	inResult := false
	for {
		tok, err := decoder.Token()
		if err != nil {
			return "", err
		}
		switch t := tok.(type) {
		case xml.StartElement:
			if t.Name.Local == "result" {
				inResult = true
			}
		case xml.CharData:
			if inResult {
				result.Write(t)
			}
		case xml.EndElement:
			switch t.Name.Local {
			case "result":
				inResult = false
			case "rule-result":
				return result.String(), nil
			}
		}
	}
}

// Config selects which scanners to run / which outputs to read.
type Config struct {
	TrivyPath       string // filesystem path for `trivy fs` ("" to skip)
	LynisReport     string // path to an existing lynis report .dat ("" to skip)
	OpenSCAPResults string // path to an OpenSCAP XCCDF results XML ("" to skip)
}

// Collect runs/reads the configured scanners and aggregates findings. The
// KISA Unix checks always run (no external tool required); the Trivy/Lynis/
// OpenSCAP scanners run only when configured.
func Collect(cfg Config) ([]Finding, error) {
	findings := make([]Finding, 0)

	findings = append(findings, CollectKISA()...)

	if cfg.TrivyPath != "" {
		trivy, err := runTrivyFS(cfg.TrivyPath)
		if err != nil {
			return nil, err
		}
		findings = append(findings, trivy...)
	}

	if cfg.LynisReport != "" {
		if data, err := os.ReadFile(cfg.LynisReport); err == nil {
			findings = append(findings, parseLynis(data)...)
		}
	}

	if cfg.OpenSCAPResults != "" {
		data, err := os.ReadFile(cfg.OpenSCAPResults)
		if err != nil {
			return nil, fmt.Errorf("read openscap results: %w", err)
		}
		oscap, err := parseOpenSCAP(data)
		if err != nil {
			return nil, err
		}
		findings = append(findings, oscap...)
	}

	return findings, nil
}

func runTrivyFS(path string) ([]Finding, error) {
	if _, err := exec.LookPath("trivy"); err != nil {
		return nil, nil
	}
	out, err := exec.Command("trivy", "fs", "--quiet", "--format", "json", path).Output()
	if err != nil {
		return nil, fmt.Errorf("run trivy fs: %w", err)
	}
	if len(strings.TrimSpace(string(out))) == 0 {
		return nil, nil
	}
	return parseTrivy(out)
}
