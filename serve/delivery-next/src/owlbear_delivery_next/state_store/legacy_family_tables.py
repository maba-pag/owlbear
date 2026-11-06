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
    ("commands/cli.py", "29d19cd3b46dd0588a919cf76835daedeb8738c2f92ac617ba5a3c10b3cce0d2"),
    ("commands/dispatch.py", "8af7e2e296eae5cd7a70dd441af65472745988da535b558121d8ab3ccbc3851c"),
    ("commands/mcp_server.py", "81a933d46accf7a13c9e666aae9b4e0a7a65b49d85f0fed32edd5c54a9dd97c9"),
    ("commands/project_commands.py", "2c43e370e6f1cf0e68cb06788a9affeef837863007334de889aaaf2427702148"),
    ("commands/runner.py", "80d7b2eaa8d4d51b068f4aa92cbc7b345e5b1ec17f1e1d400c6c55500de8e33d"),
    ("commands/setup.py", "084d7e65e3265421a4c700f72d3be93f4f88ceeaa41bcd99b0e7c6c4c8932d26"),
    ("local_system/data_place.py", "5f8e7d883c8c89fcd2b214fc5820ac48d1bc9f69ea4497c2b65b447a3beae422"),
    ("local_system/data_repo.py", "0af2ab1eebc73d4ae6aea3c4d716fb62313ad4a3dd81e66b8e4c31b79ac7be64"),
    ("local_system/git_files.py", "c7e98f34b3e5ff77d8e1b1e39cb00263a3ed57d109111e429e7d72058224783a"),
    ("local_system/git_run.py", "8819e4a78d815ebf9b79990d98217a12e2dc0523166bf7752508b1c5340862a1"),
    ("local_system/local_home.py", "793455b93decf2a9a69c152add6e45be7cdbb462272ebdd5317a6637c512fa3d"),
    ("local_system/maintenance.py", "d312367337f84f401e9fe0375e49c0f3c6b839f64cc5a2dc6662e9e81b737076"),
    ("local_system/storage_io.py", "2afa4e09b275f74decaf099826d9ecb13c57abb3fcec00651cc04458e55e6187"),
    ("machine_host/app.py", "aa4b1e0a6564dc95beb994c9c57b280596c597db0335b0fd77d0b0457c4e201d"),
    ("machine_host/command.py", "d4fa164a93d2537205851d7cf470b1b019071baea278ebd069006da3cb0e1621"),
    ("machine_host/install.py", "b1f7c06389187ec326a4a9aafced5d168de96554a615f7950ff79b21c9ff1723"),
    ("machine_host/machine.py", "5938556149cb480a252eddeac00f424c5c7c9d1aec4613d8959f39b11715e6fa"),
    ("machine_host/project.py", "033e0692c691b71c79fd6a409daf0ecba8ca162e3087491cfc1133e0b3cb289d"),
    ("state_store/registry.py", "a9f9d19675a89dc3b0494520bd2c77fcecba41e9bd682952b6d00c66ba80daea"),
    ("machine_host/selfcheck.py", "3b1ceedd24b863b1ab2419455ee748ade1e2aa34f62e9f748dae12277cdd4cbd"),
    ("impeccable_runs/pack_state.py", "40301bffd38974df0455ff3b4231cf3ff2b8824bdee11fbc18bbc1d49b3b05f0"),
    ("project_host/host.py", "9a4595c665eff22e8290aafa08e0d234931ed82b7358aa6dff590bd86c007110"),
    ("state_store/database.py", "5e50cbb36ed7e97a536b7871acde5dcff1965de3adfcc2c5ca3be14d38e514e2"),
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
