"""Whether the OwlBear code that runs on this machine is a legacy family proven to refuse the future-format fence.

The audited family is fixed data taken from the immutable commit 51aa0e1c6: per-function AST digests, per-file
module-import digests and module constants. Digests are SHA-256 of ``ast.dump(..., include_attributes=False)`` with a
leading docstring removed. A binding is the launcher, interpreter and package that actually run OwlBear. It is
accepted only when the launcher runs the interpreter that loaded the package, the package is a clean git checkout, and
every audited digest and constant matches exactly. Nothing is derived from the binding to compare against itself.
A second audited channel, the v1.0 cold chain from commit e58e0ace, is checked the same way. The current family is the
fixed candidate table for this build, pending independent review; it is literal data and never recomputed from disk at
runtime. A binding is proven when any channel matches.
"""

import ast
import copy
import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from owlbear_delivery_next.state_store.legacy_family_tables import CURRENT_MODULES, IMPORT_OVERRIDES_V151

PACKAGE = "owlbear_delivery_next"
FAMILY_AGGREGATE = "ac5947d6c0e5ec4ffb9dff2cdbd5e2a14eca0f6af55685e7db96ba68108469a3"
FUNCTIONS = (
    ("commands/chat_client.py:Chat.call", "0fc1fdb166ea555741a2aa7796a99a4eb7b71c572ad37fba1ae0a9e37171b584"),
    ("commands/chat_client.py:workspace", "d3a3e15a15d6554c1a3d9167d3b259d8890a0321c85af2df2115deaed14f13e9"),
    ("commands/cli.py:main", "cdab185067b9e4242fc97dc4df80a797460f964f69094dcc035a2920d215eebe"),
    ("commands/cli.py:update_pack", "a143193a43570b38ec6fbefe5c41e8c477eb3b3c2a988c75f60bfd518bc5f8b2"),
    ("commands/dispatch.py:main", "8c4117358586bafde31333d442b1c03a1c628b77941bbe9e1f6e95f71a577729"),
    ("commands/mcp_server.py:main", "8240f789d2bf0edce4e41a622998ce99ed379ca72c4dae8a4c18c0ce59cca6d2"),
    ("commands/runner.py:main", "05600140a349c6a3c04b8c5ef534bdf1745258f839959e5d827cb679d8f6caa6"),
    ("commands/setup.py:run", "2249dcc801faf2364fa6e2d278ecd10c0c3a096832fe8e2ea0a15cf34c63a459"),
    ("commands/step_mcp.py:forward", "6be5839cab415e4e9afba25a20afcd23eca0867e297d172882bbcd64ac0787b2"),
    ("machine_host/app.py:Dispatcher.__call__", "0a2ef7a9ebbb0903a08504ea2180d0457e837d04d385918c06855d7a93402851"),
    ("machine_host/command.py:forward", "5b6327596aa3036314e5e279f4b7a444152e7555a29059797bf2b6f0e82cca69"),
    ("machine_host/command.py:main", "b07806f0e0d2da7c59fb4e4d23f13bf545ff03b09ee49f7110da2027d5d31c36"),
    ("machine_host/install.py:doctor", "905d2d2f6a5de0db3f4a373d2c5740867bbe3f097a292719c631c26c3383a6d1"),
    ("machine_host/machine.py:Machine._load", "3b3dc14beceee8bc16d4f08ca1f16ee6bc922c5560e310d82d46bfadbf9f9ebb"),
    ("machine_host/machine.py:Machine.load_all", "70b96c5b7e2866db55db01ff96af21ca735ebaaab3f701aac367fda92aaa1370"),
    ("machine_host/machine.py:Machine.retry", "89035a3934b6da831ef697ec64561953d7e56d9bb9577ea6ce69c0155097a051"),
    ("machine_host/project.py:Project.load", "90cb161f238ce91af9469fc383d03ecb7f5225e239796463fd25cb96f5a92654"),
    ("machine_host/registry.py:adopt", "ef93858628accb92fd4cdb2b27d637513b09c502fea091f10fd8e0c571618540"),
    ("machine_host/registry.py:canonical", "b95ac624012ff18445d4e92d74028bc415c26f9c18d17e209aed4cc94cef0970"),
    ("machine_host/registry.py:register", "fa6d5044b93bb08ddc2352afd7b6ab30274c9a95a00c27113721c9a62bbc954f"),
    ("machine_host/registry.py:replaced", "5d48cb39f6ea67966760e0de397f920fd7d6ebf07f403f377fec1e56b0245231"),
    ("machine_host/selfcheck.py:_project", "57e2069ae90e55f732e86763c059f285e89636a3080e6370a0d7fb1bdd4248b0"),
    ("project_host/host.py:running_at", "5d995a0df3ec0892b8e76c19f91b265cbec48abcc8ec44fdb4f0cd192a3476a0"),
    ("state_store/project_home.py:clone_dir", "db1b925c614a629f720496a9473f955f44d686c0e8903da656e27288435f3c5d"),
    ("state_store/project_home.py:clone_id", "ab77029a725f63f8dd1936e210a4e1d74740ea333435497d401fb08d98c90e62"),
    ("state_store/project_home.py:current", "960d56eedc9cae03041ffdbe518d30f45f8bec4aba17324bb49d94d81edacab2"),
    ("state_store/project_home.py:ensure_id", "1081ce390789d1cacc0c32258a09d43eda472ca08d5988c3f4c15b1e4685e16d"),
    ("state_store/project_home.py:located", "55093b131836532fe04f079d643e1240ed428a8d0fd5f48b8fbca6a02577080f"),
    ("state_store/store.py:Store.__init__", "96ba747e5168abfb212ec2bbf0ee2bdf3e4e93e93ce829fabe2ede72bd8eef25"),
    ("state_store/store.py:Store.open", "d54cf52a601edb0aa74c4b2ca08f0e19199ccee4814d37df1201769c0dd746f8"),
)
IMPORTS = (
    ("commands/chat_client.py", "f1a06d6baaa61da9b3ccd80d563001aa92d0321541189b4977428863f47eb884"),
    ("commands/cli.py", "40598edb3983abfa575e72d3551f99246de9b0f53b493e4bbfc05971aff84488"),
    ("commands/dispatch.py", "326c281057f28ebdb70e9ddfb43e62ad0693957ce5cf2305201d67e7d4cba0e4"),
    ("commands/mcp_server.py", "1261ba9b6201136ef0dc75f1bb0f598fdf0a66a24a1f7b6f3f58b97e23b26b6a"),
    ("commands/runner.py", "65ca546d3de9d7a4fad8bd8c9ee1968c8c13150a900342465a7b9ca1509c9dce"),
    ("commands/setup.py", "c3fc48cf500984ffedb52f46a4798ee90f4f3f92ce1a82594514a879c82b1875"),
    ("commands/step_mcp.py", "6f0b962d2eac4c2e0299edf1dff7175ab9f088862c80ef9acb7d28dfec3d9748"),
    ("machine_host/app.py", "9d0bab85d66f76448e0e9bb50bda0fd2e1be8e726d77db3fc8963c2b4b81ed3d"),
    ("machine_host/command.py", "9fa9ae7ffdfbc3d49c49b4bde8775c2770186e33e5e5f1f0006ffaf1d61d079b"),
    ("machine_host/install.py", "6d603752b47fbd5ab23342933a6b44043207e1b2e94fd4a085c8a62b1d93db62"),
    ("machine_host/machine.py", "80a839c5215e013f1a6960cfad7be1a90bbbc9524406b2f631f2405e78dd5f6f"),
    ("machine_host/project.py", "abf0c82a93a364fed92c0e98f6c91a8d4fb407f37894181720eabeafa17a9353"),
    ("machine_host/registry.py", "9b665c270866f57d7056583906a29a7a0762e1aa0bc6613d70d07f614d305b76"),
    ("machine_host/selfcheck.py", "2aa2fa0c3f7e09a66cecd16cb5e0d101cd4a819bbbab976d42be1d6647fc354b"),
    ("project_host/host.py", "413bb149cd766ddbfc5adc411131394906d752d7e6fa5d8439659d6f8273fdc0"),
    ("state_store/project_home.py", "c79464a6139fe571efd600903aa848dc67c9673f016d12c093d7d6b94b74a681"),
    ("state_store/store.py", "a3da565feeee931b40d4907f17c46372c000e573e1add938ae3679d175e75de4"),
)
CURRENT_FAMILY_AGGREGATE = "bbe84730885d5758277eaa4931fa534b3dc245428bae45c5f71959e521da112d"
CURRENT_FUNCTIONS = (
    ("commands/chat_client.py:Chat.call", "0fc1fdb166ea555741a2aa7796a99a4eb7b71c572ad37fba1ae0a9e37171b584"),
    ("commands/chat_client.py:workspace", "4e1bd94f29805ab94eff49182ba65966b93988ce4a8e3f395576601499a4855d"),
    ("commands/cli.py:main", "8946fa2f7b523bbb31be79f46e3b19a8886d8300ab1c02848d19dc2bfc6131c9"),
    ("commands/cli.py:update_pack", "cff1b987d273ea7bd2cd4dc8d430c9ce1f13b26943b8d1d524f5b2c8c30152b0"),
    ("commands/dispatch.py:main", "8c4117358586bafde31333d442b1c03a1c628b77941bbe9e1f6e95f71a577729"),
    ("commands/mcp_server.py:main", "8240f789d2bf0edce4e41a622998ce99ed379ca72c4dae8a4c18c0ce59cca6d2"),
    ("commands/runner.py:main", "0bfd4e7c5dca5752bf0b82aec4032112077ec3be7f6e55ed9106857095e5ba64"),
    ("commands/setup.py:run", "dfe9cf3aef299cf7c6e72cf3c042ff12dd0c89476500092aa1c4fb775b4b9d7d"),
    ("machine_host/app.py:Dispatcher.__call__", "0a2ef7a9ebbb0903a08504ea2180d0457e837d04d385918c06855d7a93402851"),
    ("machine_host/command.py:forward", "5b6327596aa3036314e5e279f4b7a444152e7555a29059797bf2b6f0e82cca69"),
    ("machine_host/command.py:main", "b07806f0e0d2da7c59fb4e4d23f13bf545ff03b09ee49f7110da2027d5d31c36"),
    ("machine_host/install.py:doctor", "905d2d2f6a5de0db3f4a373d2c5740867bbe3f097a292719c631c26c3383a6d1"),
    ("machine_host/machine.py:Machine._load", "9d0266959ba63325df3f15ebe8ca816f855b83e5c3446fa236066cb436d99079"),
    ("machine_host/machine.py:Machine.load_all", "70b96c5b7e2866db55db01ff96af21ca735ebaaab3f701aac367fda92aaa1370"),
    ("machine_host/machine.py:Machine.retry", "89035a3934b6da831ef697ec64561953d7e56d9bb9577ea6ce69c0155097a051"),
    ("machine_host/project.py:Project.load", "90cb161f238ce91af9469fc383d03ecb7f5225e239796463fd25cb96f5a92654"),
    ("state_store/registry.py:adopt", "57e10ae159a32d7da6b2ca403f378d2af53dc7fb8ef8e0b78ed647a2d88cf7ad"),
    ("state_store/registry.py:canonical", "73a7cda1befda9f7e2b3e82a37ae61b582977b1f5bf194b012116e875dc29fa9"),
    ("state_store/registry.py:_switched", "c2978760c71196773958b52f09bf745847b30b7b41eaab6513a88561d9efe9a0"),
    ("state_store/registry.py:register", "79cb7840274422a93d94582da3f361fb56a1bbd3606dac3808d0cfdb035b255b"),
    ("state_store/registry.py:replaced", "5d48cb39f6ea67966760e0de397f920fd7d6ebf07f403f377fec1e56b0245231"),
    ("machine_host/selfcheck.py:_project", "1db6860c5035b3e805435038ae0122a1e62fe11870a185bd3de268cd2d5355fa"),
    ("machine_host/selfcheck.py:_receipt", "b37c42a3144d55fc5d634b8d9830eb8793752f3ef54ae872be420446c48e4358"),
    ("project_host/host.py:running_at", "cc129de6cc691f64d6624765bcfa54fbf82b1e29531f65c8ff16ebf7f7370d00"),
    ("state_store/offline_protocol.py:prepare", "a1bf22be92d5aed9f9643abe143b0022e87d788705b4825bf0e9ceebcabeca71"),
    (
        "state_store/offline_protocol.py:_refuse_nothing_to_move",
        "137058da364c153881a358ec9faa59d0dea41aa0c56f42aa6e3196dcdc8e9e77",
    ),
    (
        "state_store/switched_authority.py:retained_target",
        "e71f921c519345308e0ae99775698b82632c1ca57bcf88213d760d2e61d5f7fe",
    ),
    ("state_store/switched_authority.py:_proven", "823679ab6239a59c29de42e974e946e204d5a12fbf587fcb0dee419b22ef29bf"),
    ("state_store/project_home.py:_generation_at", "d048a1d7d993a3fc1fb9ad2756d4e59459e6c43fd90c604d1637de82a4c3533e"),
    ("state_store/project_home.py:clone_dir", "db1b925c614a629f720496a9473f955f44d686c0e8903da656e27288435f3c5d"),
    ("state_store/project_home.py:clone_id", "db67bbd9c2b604a58dc2ab9509ae5b9949f274f92ee64bbc65cdb215ae9b0d8b"),
    ("state_store/project_home.py:current", "d90ec79598ee4b896b04b572e9da2f644950831b8840265f8e33e207a82963ba"),
    ("state_store/project_home.py:ensure_id", "0ca91d9cd58f7a7e6f1faf1f5e7a9ae0c0c578ce58f7d798235375e280d05f5d"),
    ("state_store/project_home.py:ensure_pinned", "448d703d46f3c59a8c5856ef22adf3222ddf61d91f88e12ab1de20b0a1cf88db"),
    ("state_store/project_home.py:located", "d859e5fc314bd5c5be3e94cb2e5cdead74832ccbba657ff56ac4a29bc7ffc656"),
    ("state_store/store.py:Store.__init__", "02cdf4d6c264a0cfe2e610b3341d3612171c42b60cb1735209a4d4e228ee5764"),
    ("state_store/store.py:Store.open", "94404672c552ea7fa1354c693a2e64a9e1272455322f6aabb75290453e047481"),
)
CURRENT_IMPORTS = (
    ("commands/chat_client.py", "f1a06d6baaa61da9b3ccd80d563001aa92d0321541189b4977428863f47eb884"),
    ("commands/cli.py", "f9a6c413ed493e4f0c3ad94eb368bf85a3c896b00c3e92dfd04187d48ae5c628"),
    ("commands/dispatch.py", "326c281057f28ebdb70e9ddfb43e62ad0693957ce5cf2305201d67e7d4cba0e4"),
    ("commands/mcp_server.py", "1261ba9b6201136ef0dc75f1bb0f598fdf0a66a24a1f7b6f3f58b97e23b26b6a"),
    ("commands/runner.py", "e50e64901112d3d7e553cab2c8cbb0bdca7ac228b4c91b1ce4d3a44a8e0c9ba9"),
    ("commands/setup.py", "5317c782b9cc39a0e2dbb6816671d7a2d6219c0a9c0ec2702d368f1b01464ac9"),
    ("machine_host/app.py", "68818b17c70f19616d627b8af788e098b0a37fcd4397db9fbff73fd1b4e6afb1"),
    ("machine_host/command.py", "9fa9ae7ffdfbc3d49c49b4bde8775c2770186e33e5e5f1f0006ffaf1d61d079b"),
    ("machine_host/install.py", "8a6c8c8653d886877d9848bf7e9e01274fa4daced682ed0e1094e9db9d02543f"),
    ("machine_host/machine.py", "e8914dc14e4eecb2291a91768cb6a2c29c57c8bf6230ed4528a49d39a253b91b"),
    ("machine_host/project.py", "d8a347359ed0487e2ada6cc2de722439091e660e1496f034726ec4414e8e63ff"),
    ("state_store/registry.py", "174785f5ce9e9aae85933a328d06673ee6593bddac8cf4372d0bea5764fab83e"),
    ("machine_host/selfcheck.py", "9578776030cc7242cb20352ae35b009bdf4ac70d41fc91a08b9bac555ab4c15c"),
    ("project_host/host.py", "239bc3a5ef27a3564b59308cdbdea78efe6e73894d0da82dc740705f8ff70d5f"),
    ("state_store/project_home.py", "16a597223c63af3ad03bdd479d930d57050649c295c0f1d476f8113d42ede7d3"),
    ("state_store/store.py", "0ed9c81ba282ca264ba657b9976c294c8527d399f587cdbab8ce54e411e61aa4"),
    ("state_store/switched_authority.py", "df2480a19ffe37e7e94c3da755795d757a6ff6184f865145831ea92064529c54"),
)
CONSTANTS = (
    ("state_store/database.py", "STORE_FORMAT", 7),
    ("state_store/database.py", "MARKER", "format"),
    ("state_store/project_home.py", "STORE_DIR", "owlbear-delivery"),
    ("state_store/project_home.py", "PROJECTS", "projects"),
    ("state_store/project_home.py", "CLONE_ID", "clone-id"),
    ("state_store/project_home.py", "MOVE_LOCK", "move.lock"),
)
FILES = tuple(sorted({key.split(":")[0] for key, _ in FUNCTIONS} | {rel for rel, _, _ in CONSTANTS}))
CURRENT_CONSTANTS = (
    ("state_store/database.py", "STORE_FORMAT", 7),
    ("state_store/database.py", "MARKER", "format"),
    ("state_store/project_home.py", "STORE_DIR", "owlbear-delivery"),
    ("state_store/project_home.py", "PROJECTS", "projects"),
    ("state_store/project_move.py", "CLONE_ID", "clone-id"),
    ("state_store/project_move.py", "MOVE_LOCK", "move.lock"),
    ("state_store/project_move.py", "FENCE", "999"),
)
CURRENT_FILES = tuple(
    sorted(
        {key.split(":")[0] for key, _ in CURRENT_FUNCTIONS}
        | {rel for rel, _, _ in CURRENT_CONSTANTS}
        | {rel for rel, _ in CURRENT_MODULES}
    )
)
# The v1.0 cold channel, from commit e58e0ace4eadf44fabc775fa82adfdb2bac265e0: the MCP chain
# commands/mcp_server.py:main -> Chat.__init__ -> Store.open -> located.
# Only the rejection prefix of located is audited.
LEGACY_V1_FUNCTIONS = (
    (
        "state_store/project_home.py:ensure_id",
        "1081ce390789d1cacc0c32258a09d43eda472ca08d5988c3f4c15b1e4685e16d",
        False,
    ),
    ("commands/mcp_server.py:main", "d1044050d4995039fd509e81c8b0b42aa3b71ab4fb0cfee3b71b5933afb388bb", False),
    ("commands/mcp_server.py:Chat.__init__", "82a43902b4dc2ea8f7dac315ffd1f77b3ecb5efdd3710067b8f663995a55add4", False),
    ("state_store/store.py:Store.__init__", "96ba747e5168abfb212ec2bbf0ee2bdf3e4e93e93ce829fabe2ede72bd8eef25", False),
    ("state_store/store.py:Store.open", "d54cf52a601edb0aa74c4b2ca08f0e19199ccee4814d37df1201769c0dd746f8", False),
    ("machine_host/project.py:Project.load", "90cb161f238ce91af9469fc383d03ecb7f5225e239796463fd25cb96f5a92654", False),
    (
        "machine_host/app.py:Dispatcher.__call__",
        "0a2ef7a9ebbb0903a08504ea2180d0457e837d04d385918c06855d7a93402851",
        False,
    ),
    ("state_store/project_home.py:located", "f4753224b48ab66871e1936ec5151e6e7eb9d4b93c1d449495e00c04785e93e7", True),
)
LEGACY_V1_IMPORTS = (
    ("commands/mcp_server.py", "owlbear_delivery_next.state_store.store", ("Store", "StoreError")),
    ("state_store/store.py", "owlbear_delivery_next.state_store", ("project_home",)),
    (
        "state_store/store.py",
        "owlbear_delivery_next.state_store.database",
        ("STORE_FORMAT", "Database", "FormatTooNewError", "StoreError"),
    ),
    (
        "state_store/project_home.py",
        "owlbear_delivery_next.state_store.database",
        ("MARKER", "STORE_FORMAT", "FormatTooNewError", "StoreError"),
    ),
    ("state_store/project_home.py", "owlbear_delivery_next.local_system.git_files", ("git_common_dir",)),
    ("state_store/project_home.py", "owlbear_delivery_next.local_system", ("local_home",)),
)
LEGACY_V1_EXPRESSIONS = (("state_store/project_home.py", "KEPT", "frozenset({CLONE_ID, MARKER, MOVE_LOCK})"),)
LEGACY_V1_FILES = tuple(
    sorted(
        {key.split(":")[0] for key, _, _ in LEGACY_V1_FUNCTIONS}
        | {rel for rel, _, _ in LEGACY_V1_IMPORTS}
        | {rel for rel, _, _ in CONSTANTS}
        | {rel for rel, _, _ in LEGACY_V1_EXPRESSIONS}
    )
)


@dataclass(frozen=True)
class Gap:
    """A legacy producer that does not honour the format fence, with the exact code it is in."""

    path: str
    version: str
    reason: str


@dataclass(frozen=True)
class Binding:
    """What actually runs OwlBear: the launcher on PATH, the interpreter that loaded the package, the package."""

    launcher: Path | None
    interpreter: Path
    package: Path | None


def live_binding() -> Binding:
    """The launcher, interpreter and package that this process would actually run."""
    spec = importlib.util.find_spec(PACKAGE)
    origin = spec.origin if spec is not None else None
    launcher = shutil.which("owlbear")
    return Binding(Path(launcher) if launcher else None, Path(sys.executable), Path(origin).parent if origin else None)


def open_gaps(binding: Binding | None = None) -> tuple[Gap, ...]:
    """Return nothing only for a proven binding; otherwise one gap naming the refusal."""
    if binding is None:
        binding = live_binding()
    reason = _refusal(binding)
    if reason is None:
        return ()
    return (Gap(str(binding.package or PACKAGE), "binding", reason),)


def _refusal(binding: Binding) -> str | None:
    if binding.package is None:
        return "the owlbear_delivery_next package is not importable: unknown binding"
    return _split(binding) or _dirty(binding.package) or _code(binding.package)


def _split(binding: Binding) -> str | None:
    if binding.launcher is None:
        return "no owlbear launcher is on PATH: unknown binding"
    try:
        first = binding.launcher.read_bytes()[:512].split(b"\n", 1)[0].decode("utf-8")
    except OSError, UnicodeDecodeError:
        return "the owlbear launcher is not a text script OwlBear can inspect"
    if not first.startswith("#!") or not first[2:].split():
        return "the owlbear launcher has no interpreter line OwlBear can inspect"
    interpreter = first[2:].split()[0]
    if Path(interpreter).name == "env":
        return "the owlbear launcher starts through env, so its interpreter is unknown"
    # Not realpath: venvs share one base binary, so resolving links would hide the split.
    if os.path.abspath(interpreter) != os.path.abspath(binding.interpreter):  # noqa: PTH100
        return (
            f"split binding: the owlbear launcher runs {interpreter} "
            f"but the package was loaded by {binding.interpreter}"
        )
    return None


def _dirty(package: Path) -> str | None:
    try:
        done = subprocess.run(  # noqa: S603 - fixed argv, read-only status, no shell
            ["git", "-C", str(package), "status", "--porcelain", "--", "."],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"the git gate is unavailable ({exc.__class__.__name__}): unknown build"
    if done.returncode != 0:
        return "the package is not a git checkout: unknown build"
    if done.stdout.strip():
        return "the package checkout is dirty: refusing an unproven build"
    return None


def _code(package: Path) -> str | None:
    trees = _trees(package)
    reasons: list[str] = []
    for check in (_audited, _current, _legacy_v1):
        reason = check(trees)
        if reason is None:
            return None
        reasons.append(reason)
    return "; ".join(reasons)


def _trees(package: Path) -> dict[str, ast.Module]:
    trees: dict[str, ast.Module] = {}
    for rel in sorted(set(FILES) | set(CURRENT_FILES) | set(LEGACY_V1_FILES)):
        try:
            trees[rel] = ast.parse((package / rel).read_text(encoding="utf-8"))
        except OSError, UnicodeDecodeError, SyntaxError:
            continue
    return trees


def _missing(trees: dict[str, ast.Module], rels: tuple[str, ...]) -> str | None:
    for rel in rels:
        if rel not in trees:
            return f"{rel} is missing or unreadable: unknown build"
    return None


def _audited(trees: dict[str, ast.Module]) -> str | None:
    if (missing := _missing(trees, FILES)) is not None:
        return missing
    for rel, name, value in CONSTANTS:
        if _constant(trees[rel], name) != value:
            return f"constant {name} in {rel} is not the audited value"
    audited = _shape(trees, FUNCTIONS, IMPORTS, "the audited family")
    if audited is None:
        return None
    # The shipped v1.51 and v1.50 builds differ from 51aa only in these import digests; any other mix still refuses.
    overrides = dict(IMPORT_OVERRIDES_V151)
    shipped = tuple((rel, overrides.get(rel, digest)) for rel, digest in IMPORTS)
    released = _shape(trees, FUNCTIONS, shipped, "the v1.51 and v1.50 families")
    return None if released is None else f"{audited}; {released}"


def _current(trees: dict[str, ast.Module]) -> str | None:
    if (missing := _missing(trees, CURRENT_FILES)) is not None:
        return missing
    for rel, name, value in CURRENT_CONSTANTS:
        if _constant(trees[rel], name) != value:
            return f"current family constant {name} in {rel} is not the expected value"
    changed = [rel for rel, digest in CURRENT_MODULES if _module(trees[rel]) != digest]
    if changed:
        return "current family modules differ from the candidate: " + ", ".join(changed)
    return _shape(trees, CURRENT_FUNCTIONS, CURRENT_IMPORTS, "the current family")


def _shape(
    trees: dict[str, ast.Module],
    functions: tuple[tuple[str, str], ...],
    imports: tuple[tuple[str, str], ...],
    label: str,
) -> str | None:
    changed = [key for key, digest in functions if _function(trees[key.split(":")[0]], key.split(":")[1]) != digest]
    if changed:
        return f"functions differ from {label}: " + ", ".join(changed)
    changed = [rel for rel, digest in imports if _imports(trees[rel]) != digest]
    if changed:
        return f"module imports differ from {label}: " + ", ".join(changed)
    return None


def _legacy_v1(trees: dict[str, ast.Module]) -> str | None:
    """The v1.0 cold channel: the located rejection prefix, full chain functions, named imports and constants."""
    if (missing := _missing(trees, LEGACY_V1_FILES)) is not None:
        return missing
    changed = [
        key
        for key, digest, prefix in LEGACY_V1_FUNCTIONS
        if _function(trees[key.split(":")[0]], key.split(":")[1], prefix=prefix) != digest
    ]
    if changed:
        return "v1.0 family functions differ: " + ", ".join(changed)
    changed = [
        f"{rel} imports {module}"
        for rel, module, names in LEGACY_V1_IMPORTS
        if not _imported(trees[rel], module, names)
    ]
    if changed:
        return "v1.0 family imports differ: " + ", ".join(changed)
    for rel, name, value in CONSTANTS:
        if _constant(trees[rel], name) != value:
            return f"v1.0 family constant {name} in {rel} is not the audited value"
    for rel, name, text in LEGACY_V1_EXPRESSIONS:
        if _expression(trees[rel], name) != text:
            return f"v1.0 family constant {name} in {rel} is not the audited value"
    return None


def _imported(tree: ast.Module, module: str, names: tuple[str, ...]) -> bool:
    bound = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == module
        for alias in node.names
        if alias.asname is None
    }
    return set(names) <= bound


def _expression(tree: ast.Module, name: str) -> str | None:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.unparse(node.value)
    return None


def _function(tree: ast.Module, qualname: str, *, prefix: bool = False) -> str | None:
    body: list[ast.stmt] = tree.body
    found: ast.stmt | None = None
    for name in qualname.split("."):
        found = next(
            (
                n
                for n in body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name
            ),
            None,
        )
        if found is None:
            return None
        body = getattr(found, "body", [])
    if not isinstance(found, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None
    if _docstring(found.body):
        clone = copy.copy(found)
        clone.body = found.body[1:]
        found = clone
    if prefix:
        cut = next(
            (
                i
                for i, s in enumerate(found.body)
                if isinstance(s, ast.If) and "found > STORE_FORMAT" in ast.unparse(s.test)
            ),
            None,
        )
        if cut is None:
            return None
        clone = copy.copy(found)
        clone.body = found.body[: cut + 1]
        found = clone
    return _digest(ast.dump(found, include_attributes=False))


def _docstring(body: list[ast.stmt]) -> bool:
    first = body[0] if body else None
    return isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)


def _module(tree: ast.Module) -> str:
    return _digest(ast.dump(tree, include_attributes=False))


def _imports(tree: ast.Module) -> str:
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    return _digest(ast.dump(ast.Module(body=imports, type_ignores=[]), include_attributes=False))


def _constant(tree: ast.Module, name: str) -> object:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                return _literal(node.value)
            if isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
                for item, value in zip(target.elts, node.value.elts, strict=False):
                    if isinstance(item, ast.Name) and item.id == name:
                        return _literal(value)
    return None


def _literal(node: ast.expr) -> object:
    try:
        return ast.literal_eval(node)
    except ValueError:
        return None


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
