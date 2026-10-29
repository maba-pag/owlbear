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
    ("commands/chat_client.py", "061dff82bf8f8034ebf9cc9040a1e170645b9202510d1e1c48b75f8803333057"),
    ("commands/cli.py", "82f73b8e7a7d26f72a0a37a4fb480516ee1e1d3ef28034cccfee4cbfc61a6ca7"),
    ("commands/dispatch.py", "8af7e2e296eae5cd7a70dd441af65472745988da535b558121d8ab3ccbc3851c"),
    ("commands/mcp_server.py", "7f65bb676454919b0e5293089a411a9f8c272f694ef7fe8b0464be468d077cba"),
    ("commands/runner.py", "9816c427c457e64ce0ddd78a50aad82f68b149b71addabed4e37677ce7a66de6"),
    ("commands/setup.py", "5cf442d3a1c2f1a7e1878ab33c5c02cc904913d0cbd1e7b50011e186636afb3b"),
    ("local_system/data_place.py", "8e941dc05c74a9059bd8ceb8b9ba01bc209b3cef1f5677bfe30809cf470473ad"),
    ("local_system/data_repo.py", "c553a2a08cf42845b8ef0ceb79ee5628cffca95399ab109164d4a71f179aa423"),
    ("local_system/git_files.py", "4492e0b9805dfaf97c51c8be028cda698cff0b21587fb45c7961012177625329"),
    ("local_system/git_run.py", "ccdf414296dc12558123f5c8259a579fb1bd2da11b0050e8b8170018cb181967"),
    ("local_system/local_home.py", "9ae0858b0f9af90a86bc6630a1744279988ac6348a0f746fbd25948fd279912d"),
    ("local_system/maintenance.py", "16fcf04755321f8e64c18e564f061856316c4bcaecd54d2a087dae8822fc6d73"),
    ("local_system/storage_io.py", "2afa4e09b275f74decaf099826d9ecb13c57abb3fcec00651cc04458e55e6187"),
    ("machine_host/app.py", "168da2c05c434ed59136bb35ff36bd5f303c901da33fd70621810a07b761cc8c"),
    ("machine_host/command.py", "94259c77dd9b75372e3d7fdc0c605ab935d91ee490c783db630a3ab49958c06b"),
    ("machine_host/install.py", "97e0c5cbb230f241695725cf41494f719dce40581bb8409dd6fc4424cbd27577"),
    ("machine_host/machine.py", "2bcb0baf15a290b975614006b06b0a9dfa45d9bc2823ec44ec82641033349a39"),
    ("machine_host/project.py", "1e1aca5b919dea4cd33f0380c0a96878385f454780051b18df7eab3ff0784754"),
    ("state_store/registry.py", "b7970abe2c55d35e4da25be9efb75f765a59ddef41efa4b1ad849e7d7ecffcb9"),
    ("machine_host/selfcheck.py", "a245e8526a664828d8d9dde49e7a01292d4ea6af53721c43b2ec6b4dbd12a9df"),
    ("pack_runs/pack_state.py", "2c78fb2b0d75d96785f6b25838bcb516e6ba8ff01aaf520cece227324eae5edc"),
    ("project_host/host.py", "19e2c6e7fc46f0a897cc4fe639e1033d8a86e5e6f87de672fd3c138f6008eaaf"),
    ("state_store/database.py", "839595f61f72a0f0b8a5b3ea43295afb4009a5c4467aebd99398567320d416d7"),
    ("state_store/fd_tree.py", "1c18c4551d606cf311408badf4ce3b6d41606a7ce2fdd635907cf15ef8cebc64"),
    ("state_store/format_marker.py", "5a396d9d875098b975d3f75b9d47267a163661667c8344c258004b47668a0fec"),
    ("state_store/git_images.py", "a93719076ab2320973c3f27c789490004752fb6bf9e6d971b74d7baa8722e66b"),
    ("state_store/offline_proof.py", "626dc1e90ea7356f122d47c871b87e7656218540e089ca8717872ad332496eda"),
    ("state_store/offline_protocol.py", "3e839a8ff414e501290ff661b52e1a06f1cdbb871ac12a2a9e1527fe5acddcff"),
    ("state_store/pack_run_record.py", "1fff1709da73569fe5c8ecd10db34976ffeccdc0f38baa623ad86bd38debe220"),
    ("state_store/switched_authority.py", "cee182a0e271e5152146b07d67fa4cf576bb1829a3e40ecb50290dfb49807808"),
    ("state_store/project_home.py", "50a3d6a391c54879602a3f99a45684e45c313b00e222c48d46a93ceeac77462c"),
    ("state_store/project_move.py", "df85983badd83d2d857ec877865faf449ba9eb0d866321877ad1ae6d01a7f19e"),
    ("state_store/project_switch.py", "a33aa43982231c62d593202ba68dbcabc029829e324022d712a39b21777385e7"),
    ("state_store/store.py", "9797dc2abdc3c519ec8e4e97f0fd3183f6f498bc82a8da659ed7c3332cf3d41b"),
)
