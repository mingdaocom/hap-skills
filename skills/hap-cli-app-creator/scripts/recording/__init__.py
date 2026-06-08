"""Result recorders: console table, JSONL log, markdown/html report,
plus the per-app-folder mirror. Each implements the Recorder protocol
(``on_step`` / ``on_finish``) consumed by the executor.
"""
