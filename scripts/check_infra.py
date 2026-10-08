"""Parse infrastructure and assert key delivery invariants. Not a deployment test."""

from pathlib import Path

import yaml


class CloudFormationLoader(yaml.SafeLoader):
    pass


def intrinsic(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return {tag_suffix: loader.construct_scalar(node)}
    if isinstance(node, yaml.SequenceNode):
        return {tag_suffix: loader.construct_sequence(node)}
    return {tag_suffix: loader.construct_mapping(node)}


CloudFormationLoader.add_multi_constructor("!", intrinsic)
template = yaml.load(Path("infra/aws/template.yaml").read_text(), Loader=CloudFormationLoader)
resources = template["Resources"]
assert (
    resources["WorkQueue"]["Properties"]["VisibilityTimeout"]
    >= template["Globals"]["Function"]["Timeout"] * 6
)
assert resources["WorkerFunction"]["Properties"]["Events"]["Queue"]["Properties"][
    "FunctionResponseTypes"
] == ["ReportBatchItemFailures"]
assert resources["WorkQueue"]["Properties"]["RedrivePolicy"]["maxReceiveCount"] == 5
for file in [
    "compose.yaml",
    ".github/workflows/checks.yml",
    ".circleci/config.yml",
    "infra/k8s/workspace.yaml",
]:
    assert list(yaml.safe_load_all(Path(file).read_text()))
print("Infrastructure syntax and delivery invariants passed; cloud deployment remains unverified.")
