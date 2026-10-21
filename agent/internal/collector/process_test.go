package collector

import "testing"

func TestParseStatComm(t *testing.T) {
	cases := []struct {
		stat string
		want string
	}{
		{"1234 (nginx) S 1 1234 1234 0 -1 4194560", "nginx"},
		{"42 (my proc) R 0 42 42", "my proc"},
		{"7 ((weird)) S 1 7 7", "(weird)"},
		{"no parens here", ""},
		{"", ""},
	}
	for _, c := range cases {
		if got := parseStatComm(c.stat); got != c.want {
			t.Errorf("parseStatComm(%q) = %q, want %q", c.stat, got, c.want)
		}
	}
}
