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
    ("commands/cli.py", "9c1c0c5fd668e5776954547946948c21034039199aefdb27b443de639c892798"),
    ("commands/dispatch.py", "1ed30b1f119758a6a16345a4d1737d62f7d0500d393256ec3edcff8f2ac22984"),
    ("commands/mcp_server.py", "29fe5386b0f51906622e6cfd681d16c393a0c6b04d73fa505b3ec6ddd4bb72cd"),
    ("commands/runner.py", "886ad4fbb520a99b41511d4977d7bd17d5f282eb3dd4c65b03c132e69b59fc4a"),
    ("commands/setup.py", "0273f7a84e6583e2f51e9d831ca63380801b234648ff967d7eec18b8c503bde1"),
    ("commands/step_mcp.py", "94c3177cc5927009b80d25e2a9825f377749e2b543d1eb519b87b380ba7ee5bb"),
    ("local_system/storage_io.py", "2cb5617c08597762aedf374a6139c0eada4a38ae9de898abdcfd2df3c5251f74"),
    ("machine_host/app.py", "f2a92a135cba196a18e8b21ecc7bb7d14748585c90fce2b4614853cfc9259938"),
    ("machine_host/command.py", "47df14591c557c39773616cbeedca135d8ac02affeeeb4d1843cd17cb9c68606"),
    ("machine_host/install.py", "3e161bd1a9cce9ed3cd2a8eb1a9945f0cc53c78a801f2dfa893207707e206321"),
    ("machine_host/machine.py", "5e448311354e964047887c119f542bafa699a4013c82718167b22e2758b9627c"),
    ("machine_host/project.py", "6973cf0089a1790b4bc04556e36877ee6d1d57cbd291714a8d10bcf6328010a5"),
    ("machine_host/registry.py", "51e4ad9fa46832e1637a8c6dddc04cd4a1403fd22399c43f24153cb92602e4af"),
    ("machine_host/selfcheck.py", "ceefad22e98efb08b86c0a2240f97b95e2ce38177ec16fc9ecba17b9006ccf9e"),
    ("project_host/host.py", "b13e3538bf2cb9373550ea39084fabce719c7ffc0e2b13b85f8f7b48e8aea0ce"),
    ("state_store/database.py", "4c58bfc55a9db87a2d6aba3c52de794c06cddfce5aeb19bf3bd84c531bddc901"),
    ("state_store/fd_tree.py", "6b6d8f44a76d5d7145069d0a491ded27ff738e24cde9896fb91c49409e573e34"),
    ("state_store/offline_proof.py", "5a4fb1b44ab554ba5e1174da3ae195882284180371011e46da85f4472c344688"),
    ("state_store/offline_protocol.py", "4030b53561a6709189a2b32fbcb7309c4ed519bb47dd00e30ca97a41d7e18d1c"),
    ("state_store/switched_authority.py", "2dba49d9b9023ee60e8b2c482fb3f58da30636d5e0d3efea22158a0fa875bb55"),
    ("state_store/project_home.py", "b57f94f3b5dae4c0faa4f8463b24be377f168223440e616952eeaa4b2d0f9dc8"),
    ("state_store/project_move.py", "23820b4fbd4bece74a469c1aa434ccea7f408291cf00be34c0b7a0b69cb44337"),
    ("state_store/store.py", "c93ae35c9fb506201ebb4ba6010c4be04fd6a8fb9f9ccb3cc1522fbc5e821561"),
)
