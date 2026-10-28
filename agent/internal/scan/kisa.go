//go:build linux

// KISA Unix checks: deterministic inspection of file permissions and key
// configuration settings from the KISA『주요정보통신기반시설 기술적 취약점
// 분석·평가 방법 상세가이드』(Unix). The agent reports measured facts as
// findings (Tool "kisa"); the control-plane rule engine decides pass/fail.
//
// Only reliably automatable items are implemented here (file stat + parsing of
// /etc config files, no external scanner). The remaining KISA items stay as
// RAG-only manual guidance in the control plane.

package scan

import (
	"bufio"
	"io"
	"os"
	"strconv"
	"strings"
	"syscall"
)

// CollectKISA runs the implemented KISA Unix checks and returns findings.
func CollectKISA() []Finding {
	return []Finding{
		checkPermitRootLogin(),
		checkUniqueRootUID(),
		checkSessionTimeout(),
		checkPasswordAlgorithm(),
		filePerm("KISA-U-16", "/etc/passwd 파일 소유자 및 권한 설정", "/etc/passwd", 0o644, "high"),
		filePerm("KISA-U-18", "/etc/shadow 파일 소유자 및 권한 설정", "/etc/shadow", 0o640, "high"),
		filePerm("KISA-U-19", "/etc/hosts 파일 소유자 및 권한 설정", "/etc/hosts", 0o644, "medium"),
		filePerm("KISA-U-21", "/etc/(r)syslog.conf 파일 소유자 및 권한 설정", rsyslogPath(), 0o644, "medium"),
		filePerm("KISA-U-22", "/etc/services 파일 소유자 및 권한 설정", "/etc/services", 0o644, "low"),
		filePerm("KISA-U-37", "cron 파일 소유자 및 권한 설정", "/etc/crontab", 0o644, "medium"),
	}
}

// ---- finding builders ----

func fact(id, title, severity string, passed bool, detail string) Finding {
	p := passed
	return Finding{Tool: "kisa", CheckID: id, Title: title, Severity: severity, Passed: &p, Detail: detail}
}

func na(id, title, detail string) Finding {
	return Finding{Tool: "kisa", CheckID: id, Title: title, Severity: "info", Passed: nil, Detail: detail}
}

// ---- file permission/ownership ----

// evalPerm reports whether a file is owned by root and grants no permission bit
// beyond maxPerm (i.e. no broader than the allowed mode).
func evalPerm(mode os.FileMode, uid uint32, maxPerm os.FileMode) bool {
	return uid == 0 && mode.Perm()&^maxPerm == 0
}

func filePerm(id, title, path string, maxPerm os.FileMode, severity string) Finding {
	info, err := os.Stat(path)
	if err != nil {
		return na(id, title, path+": 파일 없음")
	}
	var uid uint32
	if st, ok := info.Sys().(*syscall.Stat_t); ok {
		uid = st.Uid
	}
	passed := evalPerm(info.Mode(), uid, maxPerm)
	detail := path + " mode=" + fmtPerm(info.Mode()) + " uid=" + strconv.FormatUint(uint64(uid), 10) +
		" max=" + fmtPerm(maxPerm)
	return fact(id, title, severity, passed, detail)
}

func fmtPerm(m os.FileMode) string {
	return "0" + strconv.FormatUint(uint64(m.Perm()), 8)
}

func rsyslogPath() string {
	if _, err := os.Stat("/etc/rsyslog.conf"); err == nil {
		return "/etc/rsyslog.conf"
	}
	return "/etc/syslog.conf"
}

// ---- config setting checks ----

func checkPermitRootLogin() Finding {
	const id, title = "KISA-U-01", "root 계정 원격 접속 제한"
	f, err := os.Open("/etc/ssh/sshd_config")
	if err != nil {
		return na(id, title, "sshd_config 없음(SSH 서버 미설치)")
	}
	defer func() { _ = f.Close() }()
	val, ok := parseLastDirective(f, "PermitRootLogin")
	if !ok {
		return fact(id, title, "high", false, "PermitRootLogin 미설정(기본 허용 위험)")
	}
	return fact(id, title, "high", strings.EqualFold(val, "no"), "PermitRootLogin="+val)
}

func checkUniqueRootUID() Finding {
	const id, title = "KISA-U-05", "root 이외의 UID가 '0' 금지"
	f, err := os.Open("/etc/passwd")
	if err != nil {
		return na(id, title, "/etc/passwd 읽기 실패")
	}
	defer func() { _ = f.Close() }()
	names := parseUID0(f)
	passed := len(names) == 1 && names[0] == "root"
	return fact(id, title, "high", passed, "UID 0 계정: "+strings.Join(names, ","))
}

func checkSessionTimeout() Finding {
	const id, title = "KISA-U-12", "Session Timeout 설정"
	paths := []string{"/etc/profile"}
	if entries, err := os.ReadDir("/etc/profile.d"); err == nil {
		for _, e := range entries {
			if strings.HasSuffix(e.Name(), ".sh") {
				paths = append(paths, "/etc/profile.d/"+e.Name())
			}
		}
	}
	for _, p := range paths {
		f, err := os.Open(p)
		if err != nil {
			continue
		}
		v, ok := parseTMOUT(f)
		_ = f.Close()
		if ok {
			return fact(id, title, "low", v > 0 && v <= 600, p+": TMOUT="+strconv.Itoa(v))
		}
	}
	return fact(id, title, "low", false, "TMOUT 미설정")
}

func checkPasswordAlgorithm() Finding {
	const id, title = "KISA-U-13", "패스워드 해시 알고리즘 설정"
	f, err := os.Open("/etc/login.defs")
	if err != nil {
		return na(id, title, "login.defs 없음")
	}
	defer func() { _ = f.Close() }()
	val, ok := parseLastDirective(f, "ENCRYPT_METHOD")
	if !ok {
		return na(id, title, "ENCRYPT_METHOD 미지정(PAM 사용 가능)")
	}
	up := strings.ToUpper(val)
	passed := up == "SHA512" || up == "SHA256" || up == "YESCRYPT"
	return fact(id, title, "medium", passed, "ENCRYPT_METHOD="+val)
}

// ---- pure parsers (unit-tested) ----

// parseLastDirective returns the value of the last non-comment "key value" line.
func parseLastDirective(r io.Reader, key string) (string, bool) {
	value := ""
	found := false
	sc := bufio.NewScanner(r)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) >= 2 && strings.EqualFold(fields[0], key) {
			value = fields[1]
			found = true
		}
	}
	return value, found
}

// parseUID0 returns the usernames in a passwd stream whose UID field is "0".
func parseUID0(r io.Reader) []string {
	var names []string
	sc := bufio.NewScanner(r)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.Split(line, ":")
		if len(parts) >= 3 && parts[2] == "0" {
			names = append(names, parts[0])
		}
	}
	return names
}

// parseTMOUT returns the first TMOUT assignment value found in a profile stream.
func parseTMOUT(r io.Reader) (int, bool) {
	sc := bufio.NewScanner(r)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		line = strings.TrimPrefix(line, "export ")
		if !strings.HasPrefix(line, "TMOUT=") {
			continue
		}
		raw := strings.TrimSpace(strings.TrimPrefix(line, "TMOUT="))
		fields := strings.Fields(raw)
		if len(fields) == 0 {
			continue
		}
		if n, err := strconv.Atoi(strings.TrimRight(fields[0], ";")); err == nil {
			return n, true
		}
	}
	return 0, false
}
