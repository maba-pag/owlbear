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
    ("commands/cli.py", "ac78a58b5d43995723d2f22987ba116d21a6c6dd82843edac20bfd535f4719f4"),
    ("commands/dispatch.py", "8af7e2e296eae5cd7a70dd441af65472745988da535b558121d8ab3ccbc3851c"),
    ("commands/mcp_server.py", "7f65bb676454919b0e5293089a411a9f8c272f694ef7fe8b0464be468d077cba"),
    ("commands/runner.py", "4a171b2af76bc6265a9bd55f15a5711fe06445b8ae8ecccd01369febc45b4bae"),
    ("commands/setup.py", "587688431e0277e32d77c81a234a5ac8d492a4c2b08365e7fd56659dcf086d03"),
    ("local_system/data_repo.py", "b4da539b8729f011405d0364d9db70d9846e107905192be308252a14e72984a4"),
    ("local_system/git_files.py", "4492e0b9805dfaf97c51c8be028cda698cff0b21587fb45c7961012177625329"),
    ("local_system/git_run.py", "51cdbc68948be8f4f16dacdaafc87d7ee5af1c36e7567570194e168b3a22281b"),
    ("local_system/local_home.py", "628406fc116eb98f7fb5697a4bc00b94e534b07a9d3cf4be430972343bc3b4a5"),
    ("local_system/maintenance.py", "be7f5d44eebd5d240f54d2363307d97be2cd61335377c605824ce61d90ff4bd1"),
    ("local_system/storage_io.py", "74b3baabe77205729ee075671348b9f41198888296c50b7239c8655b765c16ba"),
    ("machine_host/app.py", "153d868bfa75a55788c7f3ac26df9323236306dd8f01bc309dad9c1b5c180418"),
    ("machine_host/command.py", "47df14591c557c39773616cbeedca135d8ac02affeeeb4d1843cd17cb9c68606"),
    ("machine_host/install.py", "6b32a6818f1e6e5c8807520b8acf4677702b39d4b97526cb5e8881f701d086bf"),
    ("machine_host/machine.py", "bf76342e4661b824bc8a16e6bac05a0546e1c8462cf4f75dddb0bbbecf0e4b5a"),
    ("machine_host/project.py", "1e1aca5b919dea4cd33f0380c0a96878385f454780051b18df7eab3ff0784754"),
    ("state_store/registry.py", "ecc9b716fc79d765ea27fdbc09a03062fda33a5d8f96341cdb11eee7f5adfa42"),
    ("machine_host/selfcheck.py", "36d5a970f81fff35eec093a1d0f1919f698b2e245df2476cbe65f28aeb699b6e"),
    ("pack_runs/pack_state.py", "2c78fb2b0d75d96785f6b25838bcb516e6ba8ff01aaf520cece227324eae5edc"),
    ("project_host/host.py", "692c501f40c468f2ce7bce1d0a6aa74dae9099c1f4349546fb74d931e5938427"),
    ("state_store/database.py", "839595f61f72a0f0b8a5b3ea43295afb4009a5c4467aebd99398567320d416d7"),
    ("state_store/fd_tree.py", "a3d77e5dfb6d2ca63997a7a088a46e0c4ac21612a28fc209cbd5aa59f02af4bb"),
    ("state_store/format_marker.py", "6d467b553c627b69fd9b95f557f08822e9bff2fdbe133e6f09a838e3452881e2"),
    ("state_store/offline_proof.py", "5a4fb1b44ab554ba5e1174da3ae195882284180371011e46da85f4472c344688"),
    ("state_store/offline_protocol.py", "ac15beec23d9e357dfe107afdc082c9c894f884677627ef408bad163b9db245d"),
    ("state_store/pack_run_record.py", "dda1039d73c22629f0e0b08ee5a23ae43d949b2f623b974a316ac7ce61699269"),
    ("state_store/switched_authority.py", "23d989c189b622d4e3ae2b81d19c39e67b7c958233c12c6122c866157a8c3ffd"),
    ("state_store/project_home.py", "63ca029b87e6eb1e88c8f701b1401580a48130ca09f1cf9b1b2e73109ee9a0ff"),
    ("state_store/project_move.py", "01ec4975bd9044e76bb943c46e17bc2fd903b97684f344ba0b961b412c7f3054"),
    ("state_store/project_switch.py", "c925e3eead24b61322078d65e43b72dc16aedbb1601aed0d5f729ac2b93313f1"),
    ("state_store/store.py", "9797dc2abdc3c519ec8e4e97f0fd3183f6f498bc82a8da659ed7c3332cf3d41b"),
)
