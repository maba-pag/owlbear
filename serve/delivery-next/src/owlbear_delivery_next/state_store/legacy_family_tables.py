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
    ("commands/chat_client.py", "e5656da3dfcf99cef47ffb138ed0794aed5b87306e99307650ed3608fa098141"),
    ("commands/cli.py", "9cc00884946e85f8cd2d20559f296606fc9de6f5407397d0fce6fd88d8da39d5"),
    ("commands/dispatch.py", "8af7e2e296eae5cd7a70dd441af65472745988da535b558121d8ab3ccbc3851c"),
    ("commands/mcp_server.py", "85d057a0beda6f33bbf6946dc7b97ff6edc61ee51a7868983946d78b474a8ae9"),
    ("commands/project_commands.py", "2c43e370e6f1cf0e68cb06788a9affeef837863007334de889aaaf2427702148"),
    ("commands/runner.py", "581965d8559d79a6963423c4d735c30e50b7322d02686a78b5ffa695a835cff5"),
    ("commands/setup.py", "f539fb4d2b44c53abace17715eec2c7f4ddb563a0a2c596b05dace427056c267"),
    ("local_system/data_place.py", "5f8e7d883c8c89fcd2b214fc5820ac48d1bc9f69ea4497c2b65b447a3beae422"),
    ("local_system/data_repo.py", "3cc3d379cff5c850c98783b54107b6eb1931b692ea07dda548472d1ab49120dc"),
    ("local_system/git_files.py", "717d5f6dd5b8928b5a3af32567280dcebcf8b4fb3e0717799c041b5f34d5072e"),
    ("local_system/git_run.py", "8819e4a78d815ebf9b79990d98217a12e2dc0523166bf7752508b1c5340862a1"),
    ("local_system/local_home.py", "793455b93decf2a9a69c152add6e45be7cdbb462272ebdd5317a6637c512fa3d"),
    ("local_system/maintenance.py", "d312367337f84f401e9fe0375e49c0f3c6b839f64cc5a2dc6662e9e81b737076"),
    ("local_system/storage_io.py", "2afa4e09b275f74decaf099826d9ecb13c57abb3fcec00651cc04458e55e6187"),
    ("machine_host/app.py", "9ff674273cd59d4bb5919500a2876d731d08a4141458d932a603b3949e35c188"),
    ("machine_host/command.py", "d4fa164a93d2537205851d7cf470b1b019071baea278ebd069006da3cb0e1621"),
    ("machine_host/install.py", "b1f7c06389187ec326a4a9aafced5d168de96554a615f7950ff79b21c9ff1723"),
    ("machine_host/machine.py", "8e2f92a135f3ca951125896e6aa28624d4a6ab69f6db1dc3aa326bd8c8362891"),
    ("machine_host/project.py", "033e0692c691b71c79fd6a409daf0ecba8ca162e3087491cfc1133e0b3cb289d"),
    ("state_store/registry.py", "a9f9d19675a89dc3b0494520bd2c77fcecba41e9bd682952b6d00c66ba80daea"),
    ("machine_host/selfcheck.py", "ec3551686109e1739279e492a199c9a6065ad63758a956c8919d17def00f85f3"),
    ("impeccable_runs/pack_state.py", "40301bffd38974df0455ff3b4231cf3ff2b8824bdee11fbc18bbc1d49b3b05f0"),
    ("project_host/host.py", "90533d2636bac85abbf543537be5323a1b441808c08c3d2acec9dfc673eecc95"),
    ("state_store/database.py", "a054b43b3f8f94b81ba9de319582d2bbae764533839550003a6a3b3717d9c247"),
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
    ("state_store/store.py", "100ee5e0adf7acadce839e7c7e6ef2be2d9600cad68afde3868bcfde63c131f6"),
)
