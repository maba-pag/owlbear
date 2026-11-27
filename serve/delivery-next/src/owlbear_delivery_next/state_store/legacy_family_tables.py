"""Literal tables for the legacy-family verifier: the known-build import variants and the current-family modules.

These are fixed values, never recomputed from the binding. Module digests are SHA-256 of
``ast.dump(ast.parse(text), include_attributes=False)`` over the whole file, so any edit to a file on the admission
path changes its digest, including delegated settlement, ledger-schema/read and machine-home helpers.
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
    ("commands/chat_client.py", "eba84792d1f79af4b8b269dd2de11e0176e25562e6a1aecd739a675503be97c5"),
    ("commands/chat_decisions.py", "b75772e629d7b1c2864cc862493d6396bacaaf75bf92a84fdd27a68173cb17c1"),
    ("commands/cli.py", "906fae12b7203d848740aea52f7db4b7b464a4048c463c49b9c4d6027252b4be"),
    ("commands/dispatch.py", "8af7e2e296eae5cd7a70dd441af65472745988da535b558121d8ab3ccbc3851c"),
    ("commands/mcp_server.py", "4cf57a152ece10e5446ca04039ffd49af2318f24bb93bab7e7342b8a7e542fc0"),
    ("commands/project_commands.py", "3d6f564adaa5ba2906e224a09434beca22d9c7d4de37f76c7b6a5cd6b1ba9415"),
    ("commands/runner.py", "607231478301b5d49cb8c762b619a6609f949426eeb40432632fc896b3264bdf"),
    ("commands/setup.py", "330aadda34be1b8540a89cbf8d7f1798bb44cbd0c1d55466148054284046d380"),
    ("local_system/data_place.py", "fd570508a80abee600b03d5d706d68c83620e948d7796a7eef5416b2dfa9d67a"),
    ("local_system/data_repo.py", "2dfd592b00d130405686a6ff186e16cb0c0bd44b83086ad9bd55721a13ab9d38"),
    ("local_system/git_files.py", "717d5f6dd5b8928b5a3af32567280dcebcf8b4fb3e0717799c041b5f34d5072e"),
    ("local_system/git_run.py", "8819e4a78d815ebf9b79990d98217a12e2dc0523166bf7752508b1c5340862a1"),
    ("local_system/local_home.py", "793455b93decf2a9a69c152add6e45be7cdbb462272ebdd5317a6637c512fa3d"),
    ("local_system/maintenance.py", "cf7d709ccaa0b5d1e6c914be40849b7ca6e8ed8744ffc5e0a72bb104db0d8c38"),
    ("local_system/storage_io.py", "2afa4e09b275f74decaf099826d9ecb13c57abb3fcec00651cc04458e55e6187"),
    ("machine_host/app.py", "1f0a9ab471be1d6264d6d0a42f846512476a70be85453bb92070aa5af550ec04"),
    ("machine_host/command.py", "d4fa164a93d2537205851d7cf470b1b019071baea278ebd069006da3cb0e1621"),
    ("machine_host/install.py", "309283a1485613347808cff39de91915f4a4a63a44be5bb7c11cdc27e750bbfa"),
    ("machine_host/machine.py", "1a8dea525c5d6afcec7634c129a0c4bbc324fa59d1d89f31998e71088b31f9e1"),
    ("machine_host/project.py", "033e0692c691b71c79fd6a409daf0ecba8ca162e3087491cfc1133e0b3cb289d"),
    ("state_store/registry.py", "e6df31b5a6532a42387f489dd5d98a6e6eb39506d4e686f020ad5ffc7e00926c"),
    ("machine_host/selfcheck.py", "9de8ebe6ebef5712eab7cc5b6c461d8dbce3936c85b040c50a2f504663604ca1"),
    ("impeccable_runs/pack_state.py", "40301bffd38974df0455ff3b4231cf3ff2b8824bdee11fbc18bbc1d49b3b05f0"),
    ("project_host/host.py", "be3b7b60fbdd33f4ddd095d4c3103411cbe81b9f0bf7200eff92f8aee76d57ba"),
    ("state_store/database.py", "7c4a0e4bb9e752be3dfa97ca442dda1d31fa3724877669c50172d78bc97cf5fd"),
    ("state_store/fd_tree.py", "1c18c4551d606cf311408badf4ce3b6d41606a7ce2fdd635907cf15ef8cebc64"),
    ("state_store/format_marker.py", "5a396d9d875098b975d3f75b9d47267a163661667c8344c258004b47668a0fec"),
    ("state_store/git_images.py", "a93719076ab2320973c3f27c789490004752fb6bf9e6d971b74d7baa8722e66b"),
    ("state_store/offline_proof.py", "626dc1e90ea7356f122d47c871b87e7656218540e089ca8717872ad332496eda"),
    ("state_store/offline_protocol.py", "3e839a8ff414e501290ff661b52e1a06f1cdbb871ac12a2a9e1527fe5acddcff"),
    ("state_store/pack_run_record.py", "6e03c30664beff60dc18df4fa91c3b9e6c60e49ffaf784de939acde316ebafc7"),
    ("state_store/switched_authority.py", "cee182a0e271e5152146b07d67fa4cf576bb1829a3e40ecb50290dfb49807808"),
    ("state_store/project_home.py", "09b8175a64ade927a3a78ad786c6abab3bb7a2962ea5d8842ec681a35d725982"),
    ("state_store/project_move.py", "df85983badd83d2d857ec877865faf449ba9eb0d866321877ad1ae6d01a7f19e"),
    ("state_store/project_switch.py", "a33aa43982231c62d593202ba68dbcabc029829e324022d712a39b21777385e7"),
    ("state_store/store.py", "4acd5b9bbb3e706ef08f591b04b672ecf970072f57f5e0fe697ff4dc73e77656"),
)
