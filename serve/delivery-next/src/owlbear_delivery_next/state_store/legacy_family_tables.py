"""Literal tables for the legacy-family verifier: the known-build import variants and the current-family modules.

These are fixed values, never recomputed from the binding. Module digests are SHA-256 of
``ast.dump(ast.parse(text), include_attributes=False)`` over the whole file, so any edit to a file on the admission
path changes its digest, including delegated helpers such as the current ``_open_switched``.
"""

# The v1.51 and v1.50 builds differ from the audited 51aa import table in these four modules only.
# Their 30 function digests and constants match the audited family.
IMPORT_OVERRIDES_V151 = (
    ("commands/runner.py", "7bbd8280c7ede095961f94e2bb1f5a0c9b5b1656223d731d7f2babe76ee8087c"),
    ("project_host/host.py", "17053a6eaa0678860643e7912e0402b342cee2c6d33c86f96abbda9857acf9a6"),
    ("state_store/project_home.py", "3b9adf26a2f9cbc89e87170c89044ba3b04b21882ea96bf8dc8e111c13b3cf39"),
    ("state_store/store.py", "53a09113fdf49cb0dc838eb639c11bbc15b987aa91e00478bc697ccbeef5fbe7"),
)
CURRENT_MODULES = (
    ("commands/chat_client.py", "f8a9634488077d9baaa97f6888d345c58f898d8f095e86edd72bc8e3a9241490"),
    ("commands/cli.py", "cb83b6412ace59c6b194c4ba9efa5ad0285b6802c6fdcaa1be379695251c824f"),
    ("commands/dispatch.py", "1ed30b1f119758a6a16345a4d1737d62f7d0500d393256ec3edcff8f2ac22984"),
    ("commands/mcp_server.py", "29fe5386b0f51906622e6cfd681d16c393a0c6b04d73fa505b3ec6ddd4bb72cd"),
    ("commands/runner.py", "78eb34ceb7e2b7202a38fcbecd2bbfb5832a7b583bc67aac2f9378edd7951fcb"),
    ("commands/setup.py", "0273f7a84e6583e2f51e9d831ca63380801b234648ff967d7eec18b8c503bde1"),
    ("commands/step_mcp.py", "94c3177cc5927009b80d25e2a9825f377749e2b543d1eb519b87b380ba7ee5bb"),
    ("machine_host/app.py", "f2a92a135cba196a18e8b21ecc7bb7d14748585c90fce2b4614853cfc9259938"),
    ("machine_host/command.py", "47df14591c557c39773616cbeedca135d8ac02affeeeb4d1843cd17cb9c68606"),
    ("machine_host/install.py", "3e161bd1a9cce9ed3cd2a8eb1a9945f0cc53c78a801f2dfa893207707e206321"),
    ("machine_host/machine.py", "5e448311354e964047887c119f542bafa699a4013c82718167b22e2758b9627c"),
    ("machine_host/project.py", "6973cf0089a1790b4bc04556e36877ee6d1d57cbd291714a8d10bcf6328010a5"),
    ("machine_host/registry.py", "69ce9030219db9e81ee75c44cb9e501ce9ce03d6363f7c93a20111dc95938c70"),
    ("machine_host/selfcheck.py", "46d943bd54994aec5715282c0405b459c4b7b27400302afa944f155a4b3cba63"),
    ("project_host/host.py", "1f6ddaa755930923e86387615c2085f562b4c5cbb176cbc9c522229e1478a5ba"),
    ("state_store/database.py", "4c58bfc55a9db87a2d6aba3c52de794c06cddfce5aeb19bf3bd84c531bddc901"),
    ("state_store/fd_tree.py", "02a7562796f8b5abf7e915807fbbb90a1392b9c98baed2d07836ab4f315f9313"),
    ("state_store/offline_protocol.py", "15f8b6301e0df818eb6ec769b1afefeca35f88b70b62b8b6b198246235412daf"),
    ("state_store/project_home.py", "1b73b9b89b4b7fb9d44fa5ef100bce77e7cb54194923b0f20dda2f91dd466075"),
    ("state_store/project_move.py", "9b52fb4bbc46d68d72f83836e76cdcc8963a56c5dd614376518a5614ba099a6d"),
    ("state_store/store.py", "e0439c41372c84ab4bd032bb94a3daece67da8142dc72e4174398524da5a4e63"),
)
