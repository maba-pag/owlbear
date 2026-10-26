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
    ("commands/cli.py", "5e98eca3d55a2d584319bc9854e43ab20df09cf855bac966a5162d0251af0ad9"),
    ("commands/dispatch.py", "1ed30b1f119758a6a16345a4d1737d62f7d0500d393256ec3edcff8f2ac22984"),
    ("commands/mcp_server.py", "29fe5386b0f51906622e6cfd681d16c393a0c6b04d73fa505b3ec6ddd4bb72cd"),
    ("commands/runner.py", "886ad4fbb520a99b41511d4977d7bd17d5f282eb3dd4c65b03c132e69b59fc4a"),
    ("commands/setup.py", "0273f7a84e6583e2f51e9d831ca63380801b234648ff967d7eec18b8c503bde1"),
    ("commands/step_mcp.py", "94c3177cc5927009b80d25e2a9825f377749e2b543d1eb519b87b380ba7ee5bb"),
    ("local_system/storage_io.py", "d497c458216512022b85e56ef3bdf74c829d4f0e54608d957ef735c526841b30"),
    ("machine_host/app.py", "357f6a77ef59e7b2b67351dfb431e6ea519052a10c81c37c73792cceaa06005f"),
    ("machine_host/command.py", "47df14591c557c39773616cbeedca135d8ac02affeeeb4d1843cd17cb9c68606"),
    ("machine_host/install.py", "3e161bd1a9cce9ed3cd2a8eb1a9945f0cc53c78a801f2dfa893207707e206321"),
    ("machine_host/machine.py", "2e48d91b9fee8e4fe8f27af9af46b8a65d7ffd0bd07d321e3abb98b17806cc04"),
    ("machine_host/project.py", "6973cf0089a1790b4bc04556e36877ee6d1d57cbd291714a8d10bcf6328010a5"),
    ("machine_host/registry.py", "568118599431852a13173fd663e83b6764640232e4f026c065f47fc77ad79582"),
    ("machine_host/selfcheck.py", "1b5401cf5ec51dd2ffbffe4b0bc3874cf3b2105f0d0df567dde45dd4240fe18f"),
    ("project_host/host.py", "692c501f40c468f2ce7bce1d0a6aa74dae9099c1f4349546fb74d931e5938427"),
    ("state_store/database.py", "4c58bfc55a9db87a2d6aba3c52de794c06cddfce5aeb19bf3bd84c531bddc901"),
    ("state_store/fd_tree.py", "986e95d0e9c3e87e78245d4469e0680b84e499e7bd8482ef5f6f26fd229ace8d"),
    ("state_store/format_marker.py", "ff53e78b27c7932746e62fb64bf71e022948d3fd0ecbf02884773d7a6baa6d32"),
    ("state_store/offline_proof.py", "5a4fb1b44ab554ba5e1174da3ae195882284180371011e46da85f4472c344688"),
    ("state_store/offline_protocol.py", "b0d5ef44bb4b1ca8491d859bdb67a698e35d50b15aaeb5d1947743e58d1d8a1a"),
    ("state_store/switched_authority.py", "23d989c189b622d4e3ae2b81d19c39e67b7c958233c12c6122c866157a8c3ffd"),
    ("state_store/project_home.py", "552d9c5ef35cf647dfb068d3dc8c454b092fb22ae9a0873850e26520e76bbc1e"),
    ("state_store/project_move.py", "01ec4975bd9044e76bb943c46e17bc2fd903b97684f344ba0b961b412c7f3054"),
    ("state_store/project_switch.py", "c925e3eead24b61322078d65e43b72dc16aedbb1601aed0d5f729ac2b93313f1"),
    ("state_store/store.py", "c93ae35c9fb506201ebb4ba6010c4be04fd6a8fb9f9ccb3cc1522fbc5e821561"),
)
