# -*- coding: utf-8 -*-

import functools
import itertools
import unittest

import mock

from pulp.server import exceptions
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.managers.factory import initialize
from pulp.server.managers.schedule.repo import RepoSyncScheduleManager, RepoPublishScheduleManager


initialize()


@mock.patch('pulp.server.managers.schedule.repo.importer_controller')
class TestSyncList(unittest.TestCase):

    @mock.patch('pulp.server.managers.schedule.utils.get_by_resource')
    def test_validate_importer(self, mock_get_by_resource, mock_imp_ctrl):
        RepoSyncScheduleManager.list('repo1', 'importer1')
        mock_imp_ctrl.get_valid_importer.assert_called_once_with('repo1', 'importer1')

    @mock.patch('pulp.server.managers.schedule.utils.get_by_resource')
    def test_list(self, mock_get_by_resource, mock_imp_ctrl):
        ret = RepoSyncScheduleManager.list('repo1', 'importer1')

        mock_get_by_resource.assert_called_once_with(mock_imp_ctrl.build_resource_tag.return_value)
        self.assertTrue(ret is mock_get_by_resource.return_value)


@mock.patch('pulp.server.managers.schedule.repo.importer_controller.get_valid_importer')
class TestSyncCreate(unittest.TestCase):
    repo = 'repo1'
    importer = 'importer1'
    options = {'override_config': {}}
    schedule = 'PT1M'

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.save')
    @mock.patch('pulp.server.managers.schedule.utils.validate_initial_schedule_options')
    @mock.patch('pulp.server.managers.schedule.utils.validate_keys')
    def test_utils_validation(self, mock_validate_keys, mock_validate_options,
                              mock_save, mock_valid_imp):
        RepoSyncScheduleManager.create(self.repo, self.importer, self.options, self.schedule)

        mock_validate_keys.assert_called_once_with(self.options, ('override_config',))
        mock_validate_options.assert_called_once_with(self.schedule, None, True)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.save')
    def test_save(self, mock_save, *_):
        ret = RepoSyncScheduleManager.create(self.repo, self.importer, self.options,
                                             self.schedule, 3, False)

        mock_save.assert_called_once_with()
        self.assertTrue(isinstance(ret, ScheduledCall))
        self.assertEqual(ret.iso_schedule, self.schedule)
        self.assertEqual(ret.failure_threshold, 3)
        self.assertTrue(ret.enabled is False)

    @mock.patch('pulp.server.db.model.base.ObjectId', return_value='myobjectid')
    @mock.patch('pulp.server.managers.schedule.utils.delete')
    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.save')
    def test_cleanup(self, mock_save, mock_delete, mock_objectid, mock_valid_imp):

        def mock_valid_first_time_only(*args):
            mock_valid_imp.side_effect = exceptions.MissingResource

        mock_valid_imp.side_effect = mock_valid_first_time_only
        self.assertRaises(exceptions.MissingResource, RepoSyncScheduleManager.create,
                          self.repo, self.importer, self.options, self.schedule)

        mock_delete.assert_called_once_with('myobjectid')


@mock.patch('pulp.server.managers.schedule.repo.importer_controller.get_valid_importer')
class TestSyncUpdate(unittest.TestCase):
    repo = 'repo1'
    importer = 'importer1'
    schedule_id = 'schedule1'
    override = {'override_config': {'foo': 'bar'}}
    updates = {'enabled': True}

    @mock.patch('pulp.server.managers.schedule.utils.update')
    @mock.patch('pulp.server.managers.schedule.utils.validate_updated_schedule_options')
    def test_validate_options(self, mock_validate_options, mock_update, mock_valid_imp):
        RepoSyncScheduleManager.update(self.repo, self.importer, self.schedule_id, self.updates)
        mock_validate_options.assert_called_once_with(self.updates)

    @mock.patch('pulp.server.managers.schedule.utils.update')
    def test_update(self, mock_update, mock_valid_imp):
        ret = RepoSyncScheduleManager.update(self.repo, self.importer,
                                             self.schedule_id, self.updates)

        mock_update.assert_called_once_with(self.schedule_id, self.updates)
        mock_valid_imp.assert_called_once_with(self.repo, self.importer)
        # make sure it passes through the return value from utils.update
        self.assertEqual(ret, mock_update.return_value)

    @mock.patch('pulp.server.managers.schedule.utils.update')
    def test_update_overrides(self, mock_update, mock_valid_imp):
        RepoSyncScheduleManager.update(self.repo, self.importer, self.schedule_id,
                                       {'override_config': {'foo': 'bar'}})

        mock_update.assert_called_once_with(self.schedule_id,
                                            {'kwargs': {'overrides': {'foo': 'bar'}}})


@mock.patch('pulp.server.managers.schedule.repo.importer_controller.get_valid_importer')
class TestSyncDelete(unittest.TestCase):
    repo = 'repo1'
    importer = 'importer1'
    schedule_id = 'schedule1'

    @mock.patch('pulp.server.managers.schedule.utils.delete')
    def test_delete(self, mock_delete, mock_valid_imp):
        RepoSyncScheduleManager.delete(self.repo, self.importer, self.schedule_id)
        mock_valid_imp.assert_called_once_with(self.repo, self.importer)
        mock_delete.assert_called_once_with(self.schedule_id)


class TestSyncDeleteByImporterId(unittest.TestCase):
    repo = 'repo1'
    importer = 'importer1'

    @mock.patch('pulp.server.managers.schedule.repo.importer_controller')
    @mock.patch('pulp.server.managers.schedule.utils.delete_by_resource')
    def test_calls_delete_resource(self, mock_delete_by, mock_imp_ctrl):
        RepoSyncScheduleManager.delete_by_importer_id(self.repo, self.importer)
        mock_delete_by.assert_called_once_with(mock_imp_ctrl.build_resource_tag.return_value)


class TestPublishList(unittest.TestCase):

    @mock.patch('pulp.server.managers.schedule.repo.model.Distributor.objects')
    @mock.patch('pulp.server.managers.schedule.utils.get_by_resource')
    def test_list(self, mock_get_by_resource, m_dist_qs):
        ret = RepoPublishScheduleManager.list('repo1', 'distributor1')
        mock_get_by_resource.assert_called_once_with(
            m_dist_qs.get_or_404.return_value.resource_tag)
        self.assertTrue(ret is mock_get_by_resource.return_value)


@mock.patch('pulp.server.db.model.dispatch.ScheduledCall.save')
@mock.patch('pulp.server.managers.schedule.repo.model.Distributor.objects')
class TestPublishCreate(unittest.TestCase):
    repo_id = 'repo1'
    distributor_id = 'distributor1'
    options = {'override_config': {}}
    schedule = 'PT1M'

    @mock.patch('pulp.server.managers.schedule.utils.validate_initial_schedule_options')
    @mock.patch('pulp.server.managers.schedule.utils.validate_keys')
    def test_utils_validation(self, mock_validate_keys, mock_validate_options, m_dist_qs, m_save):
        RepoPublishScheduleManager.create(self.repo_id, self.distributor_id, self.options,
                                          self.schedule)

        mock_validate_keys.assert_called_once_with(self.options, ('override_config',))
        mock_validate_options.assert_called_once_with(self.schedule, None, True)

    def test_save(self, m_dist_qs, m_save):
        ret = RepoPublishScheduleManager.create(self.repo_id, self.distributor_id, self.options,
                                                self.schedule, 3, False)

        m_save.assert_called_once_with()
        self.assertTrue(isinstance(ret, ScheduledCall))
        self.assertEqual(ret.iso_schedule, self.schedule)
        self.assertEqual(ret.failure_threshold, 3)
        self.assertTrue(ret.enabled is False)

    @mock.patch('pulp.server.db.model.base.ObjectId', return_value='myobjectid')
    @mock.patch('pulp.server.managers.schedule.utils.delete')
    def test_cleanup(self, mock_delete, mock_objectid, m_dist_qs, m_save):
        """
        Ensure that a scheduled publish is removed if the distributor was deleted during create.
        """
        def fake_get(count, *args, **kwargs):
            """
            Return legit data on the first call, and raise an exception on the
            second, to simulate the distributor being deleted while a schedule
            create operation is happening.

            :type count: itertools.count
            """
            if next(count) == 0:
                return mock.MagicMock(resource_tag='mock_tag')
            else:
                raise exceptions.MissingResource

        count = itertools.count()
        m_dist_qs.get_or_404.side_effect = functools.partial(fake_get, count)

        self.assertRaises(exceptions.MissingResource, RepoPublishScheduleManager.create,
                          self.repo_id, self.distributor_id, self.options, self.schedule)

        mock_delete.assert_called_once_with('myobjectid')


@mock.patch('pulp.server.managers.schedule.repo.model.Distributor.objects')
class TestPublishUpdate(unittest.TestCase):
    repo = 'repo1'
    distributor = 'distributor1'
    schedule_id = 'schedule1'
    override = {'override_config': {'foo': 'bar'}}
    updates = {'enabled': True}

    @mock.patch('pulp.server.managers.schedule.utils.update')
    @mock.patch('pulp.server.managers.schedule.utils.validate_updated_schedule_options')
    def test_validate_options(self, mock_validate_options, mock_update, m_dist_qs):
        RepoPublishScheduleManager.update(self.repo, self.distributor, self.schedule_id,
                                          self.updates)
        mock_validate_options.assert_called_once_with(self.updates)

    @mock.patch('pulp.server.managers.schedule.utils.update')
    def test_update(self, mock_update, m_dist_qs):
        ret = RepoPublishScheduleManager.update(self.repo, self.distributor, self.schedule_id,
                                                self.updates)

        mock_update.assert_called_once_with(self.schedule_id, self.updates)
        # make sure it passes through the return value from utils.update
        self.assertEqual(ret, mock_update.return_value)

    @mock.patch('pulp.server.managers.schedule.utils.update')
    def test_update_overrides(self, mock_update, m_dist_qs):
        RepoPublishScheduleManager.update(self.repo, self.distributor, self.schedule_id,
                                          {'override_config': {'foo': 'bar'}})

        mock_update.assert_called_once_with(self.schedule_id,
                                            {'kwargs': {'overrides': {'foo': 'bar'}}})


class TestPublishDelete(unittest.TestCase):
    repo_id = 'repo1'
    distributor_id = 'distributor1'
    schedule_id = 'schedule1'

    @mock.patch('pulp.server.managers.schedule.utils.delete')
    @mock.patch('pulp.server.managers.schedule.repo.model.Distributor.objects')
    def test_delete(self, m_dist_qs, m_delete):
        RepoPublishScheduleManager.delete(self.repo_id, self.distributor_id, self.schedule_id)
        m_dist_qs.get_or_404.assert_called_once_with(repo_id=self.repo_id,
                                                     distributor_id=self.distributor_id)
        m_delete.assert_called_once_with(self.schedule_id)


class TestPublishDeleteByImporterId(unittest.TestCase):
    repo = 'repo1'
    distributor = 'distributor1'

    @mock.patch('pulp.server.managers.schedule.utils.delete_by_resource')
    @mock.patch('pulp.server.managers.schedule.repo.model.Distributor.objects')
    def test_calls_delete_resource(self, m_dist_qs, mock_delete_by):
        RepoPublishScheduleManager.delete_by_distributor_id(self.repo, self.distributor)
        distributor = m_dist_qs.get_or_404.return_value
        mock_delete_by.assert_called_once_with(distributor.resource_tag)


SCHEDULES = [
    {
        u'_id': u'529f4bd93de3a31d0ec77338',
        u'args': [u'demo1', u'puppet_distributor'],
        u'consecutive_failures': 0,
        u'enabled': True,
        u'failure_threshold': 2,
        u'first_run': u'2013-12-04T15:35:53Z',
        u'iso_schedule': u'PT1M',
        u'kwargs': {u'overrides': {}},
        u'last_run_at': u'2013-12-17T00:35:53Z',
        u'last_updated': 1387218569.811224,
        u'next_run': u'2013-12-17T00:36:53Z',
        u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\n"
                      u"ObjectId\np3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1"
                      u"\\x9a\\x00\\x10\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\n"
                      u"p10\n(lp11\nVsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\n"
                      u"Vadmin\np16\nsVpassword\np17\n"
                      u"VV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\n"
                      u"p19\nV5220ab06e19a0010e1690589\np20\ns.",
        u'remaining_runs': None,
        u'resource': u'pulp:distributor:demo:puppet_distributor',
        u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\n"
                     u"c__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\n"
                     u"sS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\n"
                     u"I0\ntp10\nRp11\nsb.",
        u'task': u'pulp.server.tasks.repository.publish',
        u'total_run_count': 1087},
    {
        u'_id': u'529f4bd93de3a31d0ec77339',
        u'args': [u'demo2', u'puppet_distributor'],
        u'consecutive_failures': 0,
        u'enabled': True,
        u'failure_threshold': None,
        u'first_run': u'2013-12-04T15:35:53Z',
        u'iso_schedule': u'PT1M',
        u'kwargs': {u'overrides': {}},
        u'last_run_at': u'2013-12-17T00:35:53Z',
        u'last_updated': 1387218500.598727,
        u'next_run': u'2013-12-17T00:36:53Z',
        u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\n"
                      u"ObjectId\np3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1" +
                      u"\\x9a\\x00\\x10\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\n" +
                      u"p10\n(lp11\nVsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\n" +
                      u"Vadmin\np16\nsVpassword\np17\n" +
                      u"VV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\n" +
                      u"p19\nV5220ab06e19a0010e1690589\np20\ns.",
        u'remaining_runs': None,
        u'resource': u'pulp:distributor:demo:puppet_distributor',
        u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\n" +
                     u"c__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\n" +
                     u"sS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\n" +
                     u"I0\ntp10\nRp11\nsb.",
        u'task': u'pulp.server.tasks.repository.publish',
        u'total_run_count': 1087},
    {
        u'_id': u'529f4bd93de3a31d0ec77340',
        u'args': [u'demo3', u'puppet_distributor'],
        u'consecutive_failures': 0,
        u'enabled': True,
        u'failure_threshold': 2,
        u'first_run': u'2013-12-04T15:35:53Z',
        u'iso_schedule': u'PT1M',
        u'kwargs': {u'overrides': {}},
        u'last_run_at': u'2013-12-17T00:35:53Z',
        u'last_updated': 1387218501.598727,
        u'next_run': u'2013-12-17T00:36:53Z',
        u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\n" +
                      u"ObjectId\np3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1" +
                      u"\\x9a\\x00\\x10\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\n" +
                      u"p10\n(lp11\nVsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\n" +
                      u"Vadmin\np16\nsVpassword\np17\n" +
                      u"VV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\n" +
                      u"p19\nV5220ab06e19a0010e1690589\np20\ns.",
        u'remaining_runs': 0,
        u'resource': u'pulp:distributor:demo:puppet_distributor',
        u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\n" +
                     u"c__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\n" +
                     u"sS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\n" +
                     "I0\ntp10\nRp11\nsb.",
        u'task': u'pulp.server.tasks.repository.publish',
        u'total_run_count': 1087,
    },
]
