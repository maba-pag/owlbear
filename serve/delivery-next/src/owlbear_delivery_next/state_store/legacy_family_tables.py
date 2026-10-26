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
    ("commands/runner.py", "ddc814dda8899939558b445104db0c6e2e044d4b805f81171fa9cdc38f883fb8"),
    ("commands/setup.py", "0273f7a84e6583e2f51e9d831ca63380801b234648ff967d7eec18b8c503bde1"),
    ("commands/step_mcp.py", "94c3177cc5927009b80d25e2a9825f377749e2b543d1eb519b87b380ba7ee5bb"),
    ("machine_host/app.py", "f2a92a135cba196a18e8b21ecc7bb7d14748585c90fce2b4614853cfc9259938"),
    ("machine_host/command.py", "47df14591c557c39773616cbeedca135d8ac02affeeeb4d1843cd17cb9c68606"),
    ("machine_host/install.py", "3e161bd1a9cce9ed3cd2a8eb1a9945f0cc53c78a801f2dfa893207707e206321"),
    ("machine_host/machine.py", "5e448311354e964047887c119f542bafa699a4013c82718167b22e2758b9627c"),
    ("machine_host/project.py", "6973cf0089a1790b4bc04556e36877ee6d1d57cbd291714a8d10bcf6328010a5"),
    ("machine_host/registry.py", "69ce9030219db9e81ee75c44cb9e501ce9ce03d6363f7c93a20111dc95938c70"),
    ("machine_host/selfcheck.py", "46d943bd54994aec5715282c0405b459c4b7b27400302afa944f155a4b3cba63"),
    ("project_host/host.py", "b13e3538bf2cb9373550ea39084fabce719c7ffc0e2b13b85f8f7b48e8aea0ce"),
    ("state_store/database.py", "4c58bfc55a9db87a2d6aba3c52de794c06cddfce5aeb19bf3bd84c531bddc901"),
    ("state_store/fd_tree.py", "4c3bd8c8aff0b96d75dff0bfe7ea30b8528200e1f2c3b83be7c3449cf48dee3b"),
    ("state_store/offline_proof.py", "6df2428ecf1ca7260a7b8e7620fd01b3ebbda49ff019272f8828e4a6e06c03a0"),
    ("state_store/offline_protocol.py", "271a25b8c9b5c3cacd999726300b18d188b5f89e15139bd0e73e90019137a0a6"),
    ("state_store/project_home.py", "62d8979444f3d08e541f98e65542cefe47b2dc1e73aea315648279ff36e73246"),
    ("state_store/project_move.py", "728486a956b1434a73e44a114edc229d4151eaf0ee8521915b02430d3d84f4b0"),
    ("state_store/store.py", "c93ae35c9fb506201ebb4ba6010c4be04fd6a8fb9f9ccb3cc1522fbc5e821561"),
)
