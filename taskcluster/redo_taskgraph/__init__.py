# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, print_function, unicode_literals

from pipes import quote as shell_quote

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.templates import merge

from six import text_type
from voluptuous import Required
from taskgraph.util.schema import taskref_or_string
from taskgraph.transforms.task import payload_builder


def register(graph_config):
    pass


transforms = TransformSequence()


@transforms.add
def fill_template(config, tasks):

    for task in tasks:
        python_version = task.pop('python-version')
        if 'tox-environment' in task:
            job_type = tox_environment = task.pop('tox-environment')
        else:
            job_type = 'tests'
            tox_environment = "py{}".format(python_version.replace('.', ''))

        taskdesc = {
            'description': "Python {} {}".format(python_version, job_type),
            'worker': {
                'docker-image': {"in-tree": "python{}".format(python_version)}
            },
            'run': {
                'using': 'run-task',
                'cwd': '{checkout}',
                'use-caches': False,
                "command": 'pip install --user tox && tox -e {}'.format(shell_quote(tox_environment)),
            }
        }
        taskdesc = merge(task, taskdesc)

        yield taskdesc


@payload_builder(
    "scriptworker-pypi",
    schema={
        # the maximum time to run, in seconds
        Required("max-run-time"): int,
        Required("action"): text_type,
        # list of artifact URLs for the artifacts that should be signed
        Required("upstream-artifacts"): [
            {
                # taskId of the task with the artifact
                Required("taskId"): taskref_or_string,
                # type of signing task (for CoT)
                Required("taskType"): text_type,
                # Paths to the artifacts to sign
                Required("paths"): [text_type],
                # Signing formats to use on each of the paths
                Required("project"): text_type,
            }
        ],
    },
)
def build_scriptworker_signing_payload(config, task, task_def):
    worker = task["worker"]

    task_def["tags"]["worker-implementation"] = "scriptworker"

    task_def["payload"] = {
        "maxRunTime": worker["max-run-time"],
        "upstreamArtifacts": worker["upstream-artifacts"],
        "action": worker['action'],
    }

    projects = set()
    for artifacts in worker["upstream-artifacts"]:
        projects.add(artifacts["project"])

    scope_prefix = config.graph_config["scriptworker"]["scope-prefix"]
    task_def["scopes"].extend(
        [
            "{}:pypi:project:{}".format(scope_prefix, project)
            for project in sorted(projects)
        ]
    )
