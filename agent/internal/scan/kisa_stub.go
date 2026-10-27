//go:build !linux

package scan

// CollectKISA is a no-op on non-Linux platforms; the KISA Unix checks rely on
// Linux file ownership (syscall.Stat_t) and /etc layout. The agent targets Linux.
func CollectKISA() []Finding { return nil }
