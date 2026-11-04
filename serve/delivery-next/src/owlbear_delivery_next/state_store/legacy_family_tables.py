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
    ("commands/chat_client.py", "8b783758baf39476f99e7308885b594e92cc07af33178c46ca448fdbe8d5b587"),
    ("commands/cli.py", "ed09425188138edd6192a758e2dee9c307f92689eff7c9489e76d63288e25ced"),
    ("commands/dispatch.py", "8af7e2e296eae5cd7a70dd441af65472745988da535b558121d8ab3ccbc3851c"),
    ("commands/mcp_server.py", "81a933d46accf7a13c9e666aae9b4e0a7a65b49d85f0fed32edd5c54a9dd97c9"),
    ("commands/project_commands.py", "2c43e370e6f1cf0e68cb06788a9affeef837863007334de889aaaf2427702148"),
    ("commands/runner.py", "b155c26b6d4731dacbcc90104fae9dac0df1bcf2d4bd2b2ccf25286020cd8518"),
    ("commands/setup.py", "de871de65343b53758ae3b7b43119f538bb462da249ccdd0d10cca9153916916"),
    ("local_system/data_place.py", "5f8e7d883c8c89fcd2b214fc5820ac48d1bc9f69ea4497c2b65b447a3beae422"),
    ("local_system/data_repo.py", "0af2ab1eebc73d4ae6aea3c4d716fb62313ad4a3dd81e66b8e4c31b79ac7be64"),
    ("local_system/git_files.py", "c7e98f34b3e5ff77d8e1b1e39cb00263a3ed57d109111e429e7d72058224783a"),
    ("local_system/git_run.py", "8819e4a78d815ebf9b79990d98217a12e2dc0523166bf7752508b1c5340862a1"),
    ("local_system/local_home.py", "793455b93decf2a9a69c152add6e45be7cdbb462272ebdd5317a6637c512fa3d"),
    ("local_system/maintenance.py", "d312367337f84f401e9fe0375e49c0f3c6b839f64cc5a2dc6662e9e81b737076"),
    ("local_system/storage_io.py", "2afa4e09b275f74decaf099826d9ecb13c57abb3fcec00651cc04458e55e6187"),
    ("machine_host/app.py", "fe5f3d190811b4f55f845edc6fb6fe86a9344822bc2cf43d814e912f49ccd08f"),
    ("machine_host/command.py", "d4fa164a93d2537205851d7cf470b1b019071baea278ebd069006da3cb0e1621"),
    ("machine_host/install.py", "e72940c4225e8fb24b446f5ae41f5ee1487dab7ed737dd5d82724cd0f23c6da9"),
    ("machine_host/machine.py", "91bfae4c3df92a241979313b14118cec7062006ad74ac9902cff0be50465263c"),
    ("machine_host/project.py", "bb751c7a8b157c2d66fea6505ee2593093866668d4b45da6286707889bc2602a"),
    ("state_store/registry.py", "a9f9d19675a89dc3b0494520bd2c77fcecba41e9bd682952b6d00c66ba80daea"),
    ("machine_host/selfcheck.py", "3b1ceedd24b863b1ab2419455ee748ade1e2aa34f62e9f748dae12277cdd4cbd"),
    ("impeccable_runs/pack_state.py", "40301bffd38974df0455ff3b4231cf3ff2b8824bdee11fbc18bbc1d49b3b05f0"),
    ("project_host/host.py", "86c4dcd6904dd97b4e319a103c5d27c597435b8a7c4bcff421585ca6b9410d57"),
    ("state_store/database.py", "839595f61f72a0f0b8a5b3ea43295afb4009a5c4467aebd99398567320d416d7"),
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
    ("state_store/store.py", "eb8177263e260cdcdaeb584c3e679a21960961e531f6729d3e0f2b2d2e7e99de"),
)
