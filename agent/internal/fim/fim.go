// Package fim computes file-integrity manifests: SHA-256 hashes of monitored
// files plus the agent's own binary hash (self-protection). The control plane
// stores a baseline and diffs subsequent manifests to detect tampering.
package fim

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
)

// FileEntry is one monitored file's integrity record.
type FileEntry struct {
	Path   string `json:"path"`
	SHA256 string `json:"sha256"`
	Size   int64  `json:"size"`
	Mode   string `json:"mode"`
}

// Manifest is a point-in-time integrity snapshot.
type Manifest struct {
	AgentSHA256 string      `json:"agent_sha256"`
	Files       []FileEntry `json:"files"`
}

func hashFile(path string) (sum string, size int64, mode string, err error) {
	info, err := os.Stat(path)
	if err != nil {
		return "", 0, "", err
	}
	file, err := os.Open(path)
	if err != nil {
		return "", 0, "", err
	}
	defer func() { _ = file.Close() }()

	hasher := sha256.New()
	if _, err := io.Copy(hasher, file); err != nil {
		return "", 0, "", err
	}
	return hex.EncodeToString(hasher.Sum(nil)), info.Size(), fmt.Sprintf("%04o", info.Mode().Perm()), nil
}

// Scan hashes each path. Directories are walked for regular files; unreadable
// entries are skipped (e.g. /etc/shadow when not root). The agent's own binary
// hash is recorded in AgentSHA256.
func Scan(paths []string) Manifest {
	manifest := Manifest{Files: make([]FileEntry, 0)}
	for _, path := range paths {
		info, err := os.Stat(path)
		if err != nil {
			continue
		}
		if info.IsDir() {
			walkDir(path, &manifest)
			continue
		}
		if sum, size, mode, err := hashFile(path); err == nil {
			manifest.Files = append(manifest.Files, FileEntry{Path: path, SHA256: sum, Size: size, Mode: mode})
		}
	}
	if sum, err := selfHash(); err == nil {
		manifest.AgentSHA256 = sum
	}
	return manifest
}

func walkDir(root string, manifest *Manifest) {
	_ = filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() || !d.Type().IsRegular() {
			return nil
		}
		if sum, size, mode, hErr := hashFile(path); hErr == nil {
			manifest.Files = append(manifest.Files, FileEntry{Path: path, SHA256: sum, Size: size, Mode: mode})
		}
		return nil
	})
}

func selfHash() (string, error) {
	exe, err := os.Executable()
	if err != nil {
		return "", err
	}
	sum, _, _, err := hashFile(exe)
	return sum, err
}
