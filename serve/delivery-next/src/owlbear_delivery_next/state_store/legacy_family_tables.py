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
    ("commands/cli.py", "f8b89226ae7d05ecc6a3fdb026e4a94fedafa4b5aa9d4e35694477ca2d2f9f4e"),
    ("commands/dispatch.py", "8af7e2e296eae5cd7a70dd441af65472745988da535b558121d8ab3ccbc3851c"),
    ("commands/mcp_server.py", "7f65bb676454919b0e5293089a411a9f8c272f694ef7fe8b0464be468d077cba"),
    ("commands/runner.py", "9816c427c457e64ce0ddd78a50aad82f68b149b71addabed4e37677ce7a66de6"),
    ("commands/setup.py", "587688431e0277e32d77c81a234a5ac8d492a4c2b08365e7fd56659dcf086d03"),
    ("local_system/data_repo.py", "b4da539b8729f011405d0364d9db70d9846e107905192be308252a14e72984a4"),
    ("local_system/git_files.py", "4492e0b9805dfaf97c51c8be028cda698cff0b21587fb45c7961012177625329"),
    ("local_system/git_run.py", "51cdbc68948be8f4f16dacdaafc87d7ee5af1c36e7567570194e168b3a22281b"),
    ("local_system/local_home.py", "628406fc116eb98f7fb5697a4bc00b94e534b07a9d3cf4be430972343bc3b4a5"),
    ("local_system/maintenance.py", "be7f5d44eebd5d240f54d2363307d97be2cd61335377c605824ce61d90ff4bd1"),
    ("local_system/storage_io.py", "2afa4e09b275f74decaf099826d9ecb13c57abb3fcec00651cc04458e55e6187"),
    ("machine_host/app.py", "f99ca18d20f29e7d13137229472d4b3250faf95b015d9566bb3757c59da2c014"),
    ("machine_host/command.py", "0b52f45d04208ad576cb9b498ec8f4f2002e0ece505c5390e867ef429f44d6c8"),
    ("machine_host/install.py", "6b32a6818f1e6e5c8807520b8acf4677702b39d4b97526cb5e8881f701d086bf"),
    ("machine_host/machine.py", "ff113bcabdaaa2e97193b88666a908b68b3f1ad835c3c134135b203cea9c3d3f"),
    ("machine_host/project.py", "1e1aca5b919dea4cd33f0380c0a96878385f454780051b18df7eab3ff0784754"),
    ("state_store/registry.py", "2c4e97d3bf955945090ce8ada139cedb744f323d44896468f2100cde65bfa1f2"),
    ("machine_host/selfcheck.py", "584261be4e669b4fea2a9b326878e969c45271d0ce0087afcb4fb5fafa24f3e1"),
    ("pack_runs/pack_state.py", "2c78fb2b0d75d96785f6b25838bcb516e6ba8ff01aaf520cece227324eae5edc"),
    ("project_host/host.py", "692c501f40c468f2ce7bce1d0a6aa74dae9099c1f4349546fb74d931e5938427"),
    ("state_store/database.py", "839595f61f72a0f0b8a5b3ea43295afb4009a5c4467aebd99398567320d416d7"),
    ("state_store/fd_tree.py", "badfefc58f61766b7c0a545cc4972c9bfe071dd9f0fcc878a39912d73b4dc6ae"),
    ("state_store/format_marker.py", "2a538b34a03c520a1db89dc163ce8b413b1f4112374bdc7ff66d688730e7dda0"),
    ("state_store/offline_proof.py", "c5d54269e278331d3f1466f0b3796f00e9d1b5329714e26126adad880007366b"),
    ("state_store/offline_protocol.py", "3e839a8ff414e501290ff661b52e1a06f1cdbb871ac12a2a9e1527fe5acddcff"),
    ("state_store/pack_run_record.py", "af8fcff2c1d1396435a63f5da36b0d0e61c946ea8fce8a6a3c29366cbd793981"),
    ("state_store/switched_authority.py", "fc566276bb7d7fcb718ad6709e1a3d773dd0d1dad43e75d8a7315d58934a6e4f"),
    ("state_store/project_home.py", "ea8237dbd3b611d5fbd86129d0eeec110d9b7c058778e53ac3170a982935c719"),
    ("state_store/project_move.py", "ec1d2213f45ce1ad738d59821cfa2f65d15496d4b667b600cb078b31a32aa434"),
    ("state_store/project_switch.py", "62709eca0fcf6aae1e99dd82032286ce0af43211dcad0b1f63980ca83f2aec38"),
    ("state_store/store.py", "9797dc2abdc3c519ec8e4e97f0fd3183f6f498bc82a8da659ed7c3332cf3d41b"),
)
