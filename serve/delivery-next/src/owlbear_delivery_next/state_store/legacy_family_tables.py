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
    ("commands/chat_client.py", "8d4674021d32d3171e27cea7682f96615cf323a766fb01c3d961d82c3d63321a"),
    ("commands/cli.py", "83a22fe30e7eabe897c1cc01dc12c01b9295128a52db3e0f92214fbea856b265"),
    ("commands/dispatch.py", "8af7e2e296eae5cd7a70dd441af65472745988da535b558121d8ab3ccbc3851c"),
    ("commands/mcp_server.py", "9e84bd5960bbc20d16ce3c2f7ba4009db5894b6b31111128481b56bf02a31b7f"),
    ("commands/project_commands.py", "92e4b4d4b087b9233b29b35f5dbc1d067117a0d48c247697b83b0a2bce2861e7"),
    ("commands/runner.py", "2dd37f7ffb2d281740a2002b0681c8fb1d3bf0b38e5457efb9a5018e657a8193"),
    ("commands/setup.py", "f9588b801c6c787e7e00d260975dadc03e1daaa0b5f30f8ad8dd0fe6aebab330"),
    ("local_system/data_place.py", "ffed18f2758ecc539c0ec2f3dd0292ea11d7209918be1c260c2e531891e16622"),
    ("local_system/data_repo.py", "8efae8306c0664d7f4431a5230d1f9b8ea98daecf177a80cea83123b5a72c4f2"),
    ("local_system/git_files.py", "4492e0b9805dfaf97c51c8be028cda698cff0b21587fb45c7961012177625329"),
    ("local_system/git_run.py", "ccdf414296dc12558123f5c8259a579fb1bd2da11b0050e8b8170018cb181967"),
    ("local_system/local_home.py", "793455b93decf2a9a69c152add6e45be7cdbb462272ebdd5317a6637c512fa3d"),
    ("local_system/maintenance.py", "16fcf04755321f8e64c18e564f061856316c4bcaecd54d2a087dae8822fc6d73"),
    ("local_system/storage_io.py", "2afa4e09b275f74decaf099826d9ecb13c57abb3fcec00651cc04458e55e6187"),
    ("machine_host/app.py", "fdf6e66eb2f745515c8991541b2b502024bb6dfd06ccf1e442028983fba23feb"),
    ("machine_host/command.py", "d4fa164a93d2537205851d7cf470b1b019071baea278ebd069006da3cb0e1621"),
    ("machine_host/install.py", "97e0c5cbb230f241695725cf41494f719dce40581bb8409dd6fc4424cbd27577"),
    ("machine_host/machine.py", "ba3652057ddcc9fd6df4cd98ae089819487393f6b22ad2a0138442a95aa5fa50"),
    ("machine_host/project.py", "b25d6627480ca19e865bcd3dbf075b0b512f19bc642857e0d104570408771386"),
    ("state_store/registry.py", "b38e2140ad5e1ca8d057d7bec4c2f3850d0f901527b6598374de665ffcbae798"),
    ("machine_host/selfcheck.py", "a245e8526a664828d8d9dde49e7a01292d4ea6af53721c43b2ec6b4dbd12a9df"),
    ("impeccable_runs/pack_state.py", "40301bffd38974df0455ff3b4231cf3ff2b8824bdee11fbc18bbc1d49b3b05f0"),
    ("project_host/host.py", "56d8797f7b8675f5c0e136556f4aec951a204641a7549e4a2d6a1056dd2fe5d3"),
    ("state_store/database.py", "839595f61f72a0f0b8a5b3ea43295afb4009a5c4467aebd99398567320d416d7"),
    ("state_store/fd_tree.py", "1c18c4551d606cf311408badf4ce3b6d41606a7ce2fdd635907cf15ef8cebc64"),
    ("state_store/format_marker.py", "5a396d9d875098b975d3f75b9d47267a163661667c8344c258004b47668a0fec"),
    ("state_store/git_images.py", "a93719076ab2320973c3f27c789490004752fb6bf9e6d971b74d7baa8722e66b"),
    ("state_store/offline_proof.py", "626dc1e90ea7356f122d47c871b87e7656218540e089ca8717872ad332496eda"),
    ("state_store/offline_protocol.py", "3e839a8ff414e501290ff661b52e1a06f1cdbb871ac12a2a9e1527fe5acddcff"),
    ("state_store/pack_run_record.py", "6e03c30664beff60dc18df4fa91c3b9e6c60e49ffaf784de939acde316ebafc7"),
    ("state_store/switched_authority.py", "cee182a0e271e5152146b07d67fa4cf576bb1829a3e40ecb50290dfb49807808"),
    ("state_store/project_home.py", "af3c86a96f9d438e61a01c0a265548ada6b05864a2ebd99f48d0545251d6580a"),
    ("state_store/project_move.py", "df85983badd83d2d857ec877865faf449ba9eb0d866321877ad1ae6d01a7f19e"),
    ("state_store/project_switch.py", "a33aa43982231c62d593202ba68dbcabc029829e324022d712a39b21777385e7"),
    ("state_store/store.py", "1bebdf9fe96cf0674b523540cbf419736680a9e154ecf55ab781e231a2283e49"),
)
