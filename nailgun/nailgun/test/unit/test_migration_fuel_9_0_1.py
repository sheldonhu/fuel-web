#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime

import alembic

from nailgun.db import db
from nailgun.db import dropdb
from nailgun.db.migration import ALEMBIC_CONFIG
from nailgun.test import base
from oslo_serialization import jsonutils
import sqlalchemy as sa

_prepare_revision = '11a9adc6d36a'
_test_revision = '675105097a69'


def setup_module():
    dropdb()
    alembic.command.upgrade(ALEMBIC_CONFIG, _prepare_revision)
    prepare()
    alembic.command.upgrade(ALEMBIC_CONFIG, _test_revision)


def prepare():
    meta = base.reflect_db_metadata()

    result = db.execute(
        meta.tables['releases'].insert(),
        [{
            'name': 'test_name',
            'version': '2015.1-8.0',
            'operating_system': 'ubuntu',
            'state': 'available',
            'networks_metadata': jsonutils.dumps({
                'neutron': {
                    'networks': [],
                    'config': {}
                }
            })
        }]
    )
    releaseid = result.inserted_primary_key[0]

    db.execute(
        meta.tables['clusters'].insert(),
        [{
            'name': 'test_env',
            'release_id': releaseid,
            'mode': 'ha_compact',
            'status': 'new',
            'net_provider': 'neutron',
            'grouping': 'roles',
            'fuel_version': '8.0',
            'deployment_tasks': '[]',
            'replaced_deployment_info': '{}'
        }])

    db.commit()


class TestDeploymentHistoryMigration(base.BaseAlembicMigrationTest):
    def test_history_has_task_name_status_idx_index(self):
        tbl = self.meta.tables['deployment_history']
        self.assertIn('deployment_history_task_name_status_idx',
                      [i.name for i in tbl.indexes])


class TestClusterReplacedDeploymentInfo(base.BaseAlembicMigrationTest):

    def test_cluster_replaced_deployment_info_corrected(self):
        clusters_table = self.meta.tables['clusters']
        columns = [clusters_table.c.replaced_deployment_info]
        cluster = db.execute(sa.select(columns)).fetchone()
        self.assertEqual(cluster.replaced_deployment_info, '[]')


class TestTasksSnapshotField(base.BaseAlembicMigrationTest):
    def test_fields_exist(self):
        db.execute(
            self.meta.tables['tasks'].insert(),
            [{
                'uuid': 'fake_task_uuid_0',
                'name': 'dump',
                'status': 'pending',
                'tasks_snapshot': '[{"id":"taskid","type":"puppet"}]'
            }]
        )
        result = db.execute(
            sa.select([
                self.meta.tables['tasks'].c.tasks_snapshot,
            ])
        ).first()
        self.assertIsNotNone(result['tasks_snapshot'])


class TestTransactionsNames(base.BaseAlembicMigrationTest):

    def test_fields_exist(self):
        db.execute(
            self.meta.tables['tasks'].insert(),
            [
                {
                    'uuid': 'fake_task_uuid_0',
                    'name': 'dry_run_deployment',
                    'status': 'pending'
                }
            ]
        )


class TestNodeErrorMessage(base.BaseAlembicMigrationTest):

    def test_upgrade_node_error_msg_to_allow_long_error_msg(self):
        nodes = self.meta.tables['nodes']
        self.assertIsInstance(nodes.columns['error_msg'].type, sa.Text)

        node_uuid = '26b508d0-0d76-4159-bce9-f67ec2765480'
        long_error_msg = ''.join('a' for i in range(500))

        db.execute(
            nodes.insert(),
            [{
                'uuid': node_uuid,
                'cluster_id': None,
                'group_id': None,
                'status': 'discover',
                'meta': '{}',
                'mac': 'aa:aa:aa:aa:aa:aa',
                'error_msg': long_error_msg,
                'timestamp': datetime.datetime.utcnow(),
            }]
        )

        node = db.query(nodes).filter_by(uuid=node_uuid).first()
        self.assertEqual(long_error_msg, node.error_msg)
