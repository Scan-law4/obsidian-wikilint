"""VaultCompat — obsidian_parser.Vault with the hidden-ancestor bug fixed.

Bug (obsidianmd-parser 0.4.1, vault.py line ~81): _get_all_file_paths()
drops any file whose ABSOLUTE path contains a component starting with
".". A vault under a hidden directory (e.g. ~/.hermes/profiles/mom/wiki)
therefore indexes as 0 notes and every index-based API (notes,
find_broken_links, name resolution) silently returns empty.

Fix: apply the hidden-component filter to the path RELATIVE to the vault
root, so hidden files/dirs INSIDE the vault (.obsidian/, .trash/) are
still excluded, but hidden ancestors above the vault root are not.

Everything else in Vault derives file discovery from
_get_all_file_paths(), so this single override restores the whole API
surface. Verified against vault.py source: it is the only site with the
hidden-component filter (grep 'startswith' across the package).

Status: workaround, couples to a private method — hence the <0.5 pin in
pyproject.toml. Report upstream; delete this module when fixed.
"""
from pathlib import Path

from obsidian_parser import Vault


class VaultCompat(Vault):
    """Vault that works when the vault root lives under a hidden directory."""

    def _get_all_file_paths(self) -> list[Path]:
        if self._file_paths is None:
            self._file_paths = [
                p
                for p in self.path.rglob("*")
                if p.is_file()
                and not any(
                    part.startswith(".")
                    for part in p.relative_to(self.path).parts
                )
            ]
        return self._file_paths
