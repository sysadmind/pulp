# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Importer plugin for Yum functionality
"""
import gettext
import logging
import os
import time

import drpm
import errata
import importer_rpm
import distribution
from pulp.server.content.plugins.importer import Importer
from pulp.yum_plugin import util

_ = gettext.gettext
_LOG = logging.getLogger(__name__)
#TODO Fix up logging so we log to a separate file to aid debugging
#_LOG.addHandler(logging.FileHandler('/var/log/pulp/yum-importer.log'))

YUM_IMPORTER_TYPE_ID="yum_importer"

REQUIRED_CONFIG_KEYS = ['feed_url']
OPTIONAL_CONFIG_KEYS = ['ssl_verify', 'ssl_ca_cert', 'ssl_client_cert', 'ssl_client_key',
                        'proxy_url', 'proxy_port', 'proxy_pass', 'proxy_user',
                        'max_speed', 'verify_size', 'verify_checksum', 'num_threads',
                        'newest', 'remove_old', 'num_old_packages', 'purge_orphaned', 'skip_content_types', 'checksum_type']
###
# Config Options Explained
###
# feed_url: Repository URL
# ssl_verify: True/False to control if yum/curl should perform SSL verification of the host
# ssl_ca_cert: Path to SSL CA certificate used for ssl verification
# ssl_client_cert: Path to SSL Client certificate, used for protected repository access
# ssl_client_key: Path to SSL Client key, used for protected repository access
# proxy_url: Proxy URL 
# proxy_port: Port Port
# proxy_user: Username for Proxy
# proxy_pass: Password for Proxy
# max_speed: Limit the Max speed in KB/sec per thread during package downloads
# verify_checksum: if True will verify the checksum for each existing package repo metadata
# verify_size: if True will verify the size for each existing package against repo metadata
# num_threads: Controls number of threads to use for package download (technically number of processes spawned)
# newest: Boolean option, if True only download the latest packages
# remove_old: Boolean option, if True remove old packages
# num_old_packages: Defaults to 0, controls how many old packages to keep if remove_old is True
# purge_orphaned: Defaults to True, when True will delete packages no longer available from the source repository
# skip_content_types: List of what content types to skip during sync, options:
#                     ["rpm", "drpm", "errata", "distribution", "packagegroup"]
# checksum_type: checksum type to use for repodata; defaults to source checksum type or sha256

class YumImporter(Importer):
    @classmethod
    def metadata(cls):
        return {
            'id'           : YUM_IMPORTER_TYPE_ID,
            'display_name' : 'Yum Importer',
            'types'        : [importer_rpm.RPM_TYPE_ID, importer_rpm.SRPM_TYPE_ID, errata.ERRATA_TYPE_ID, drpm.DRPM_TYPE_ID,
                              distribution.DISTRO_TYPE_ID]
        }

    def validate_config(self, repo, config, related_repos):
        _LOG.info("validate_config invoked, config values are: %s" % (config.repo_plugin_config))
        for key in REQUIRED_CONFIG_KEYS:
            if key not in config.repo_plugin_config:
                msg = _("Missing required configuration key: %(key)s" % {"key":key})
                _LOG.error(msg)
                return False, msg
            if key == 'feed_url':
                feed_url = config.get('feed_url')
                if not util.validate_feed(feed_url):
                    msg = _("feed_url [%s] does not start with a valid protocol" % feed_url)
                    _LOG.error(msg)
                    return False, msg

        for key in config.repo_plugin_config:
            if key not in REQUIRED_CONFIG_KEYS and key not in OPTIONAL_CONFIG_KEYS:
                msg = _("Configuration key '%(key)s' is not supported" % {"key":key})
                _LOG.error(msg)
                return False, msg
            if key == 'ssl_verify':
                ssl_verify = config.get('ssl_verify')
                if ssl_verify is not None and not isinstance(ssl_verify, bool) :
                    msg = _("ssl_verify should be a boolean; got %s instead" % ssl_verify)
                    _LOG.error(msg)
                    return False, msg

            if key == 'ssl_ca_cert':
                ssl_ca_cert = config.get('ssl_ca_cert')
                if ssl_ca_cert is not None:
                    if not util.validate_cert(ssl_ca_cert) :
                        msg = _("ssl_ca_cert is not a valid certificate")
                        _LOG.error(msg)
                        return False, msg

            if key == 'ssl_client_cert':
                ssl_client_cert = config.get('ssl_client_cert')
                if ssl_client_cert is not None:
                    if not util.validate_cert(ssl_client_cert) :
                        msg = _("ssl_client_cert is not a valid certificate")
                        _LOG.error(msg)
                        return False, msg
            if key == 'proxy_url':
                proxy_url = config.get('proxy_url')
                if proxy_url is not None and not util.validate_feed(proxy_url):
                    msg = _("Invalid proxy url: %s" % proxy_url)
                    _LOG.error(msg)
                    return False, msg

            if key == 'proxy_port':
                proxy_port = config.get('proxy_port')
                if proxy_port is not None and isinstance(proxy_port, int):
                    msg = _("Invalid proxy port: %s" % proxy_port)
                    _LOG.error(msg)
                    return False, msg

            if key == 'verify_checksum':
                verify_checksum = config.get('verify_checksum')
                if verify_checksum is not None and not isinstance(verify_checksum, bool) :
                    msg = _("verify_checksum should be a boolean; got %s instead" % verify_checksum)
                    _LOG.error(msg)
                    return False, msg

            if key == 'verify_size':
                verify_size = config.get('verify_size')
                if verify_size is not None and not isinstance(verify_size, bool) :
                    msg = _("verify_size should be a boolean; got %s instead" % verify_size)
                    _LOG.error(msg)
                    return False, msg

            if key == 'max_speed':
                max_speed = config.get('max_speed')
                if max_speed is not None and not isinstance(max_speed, int) :
                    msg = _("max_speed should be an integer; got %s instead" % max_speed)
                    _LOG.error(msg)
                    return False, msg

            if key == 'num_threads':
                num_threads = config.get('num_threads')
                if num_threads is not None and not isinstance(num_threads, int) :
                    msg = _("num_threads should be an integer; got %s instead" % num_threads)
                    _LOG.error(msg)
                    return False, msg

            if key == 'newest':
                newest = config.get('newest')
                if newest is not None and not isinstance(newest, bool) :
                    msg = _("newest should be a boolean; got %s instead" % newest)
                    _LOG.error(msg)
                    return False, msg
            if key == 'remove_old':
                remove_old = config.get('remove_old')
                if remove_old is not None and not isinstance(remove_old, bool) :
                    msg = _("newest should be a boolean; got %s instead" % remove_old)
                    _LOG.error(msg)
                    return False, msg

            if key == 'num_old_packages':
                num_old_packages = config.get('num_old_packages')
                if num_old_packages is not None and not isinstance(num_old_packages, int) :
                    msg = _("num_old_packages should be an integer; got %s instead" % num_old_packages)
                    _LOG.error(msg)
                    return False, msg

            if key == 'purge_orphaned':
                purge_orphaned = config.get('purge_orphaned')
                if purge_orphaned is not None and not isinstance(purge_orphaned, bool) :
                    msg = _("purge_orphaned should be a boolean; got %s instead" % purge_orphaned)
                    _LOG.error(msg)
                    return False, msg

            if key == 'skip_content_types':
                skip = config.get('skip_content_types')
                if skip is not None and not isinstance(skip, list):
                    msg = _("skip_content_types should be a list; got %s instead" % skip)
                    _LOG.error(msg)
                    return False, msg

            if key == 'checksum_type':
                checksum_type = config.get('checksum_type')
                if checksum_type is not None and not util.is_valid_checksum_type(checksum_type):
                    msg = _("%s is not a valid checksum type" % checksum_type)
                    _LOG.error(msg)
                    return False, msg

        return True, None

    def importer_added(self, repo, config):
        _LOG.info("importer_added invoked")

    def importer_removed(self, repo, config):
        _LOG.info("importer_removed invoked")

    def import_units(self, source_repo, dest_repo, import_conduit, config, units=None):
        """
        @param source_repo: metadata describing the repository containing the
               units to import
        @type  source_repo: L{pulp.server.content.plugins.data.Repository}

        @param dest_repo: metadata describing the repository to import units
               into
        @type  dest_repo: L{pulp.server.content.plugins.data.Repository}

        @param import_conduit: provides access to relevant Pulp functionality
        @type  import_conduit: L{pulp.server.content.conduits.unit_import.ImportUnitConduit}

        @param config: plugin configuration
        @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

        @param units: optional list of pre-filtered units to import
        @type  units: list of L{pulp.server.content.plugins.data.Unit}
        """
        if not units:
            # If no units are passed in, assume we will use all units from source repo
            units = import_conduit.get_source_units()
        _LOG.info("Importing %s units from %s to %s" % (len(units), source_repo.id, dest_repo.id))
        for u in units:
            # We are assuming that Pulp is telling us about units which already exist in Pulp
            # therefore they have already been downloaded and written to the correct location on the filesystem
            # i.e. we are assuming unit.storage_path is correct and points to the actual unit if appropriate (non-errata, etc).
            #
            if u.unit_key.has_key("filename") and u.storage_path:
                sym_link = os.path.join(dest_repo.working_dir, dest_repo.id, u.unit_key["filename"])
                if os.path.lexists(sym_link):
                    remove_link = True
                    if os.path.islink(sym_link):
                        existing_link_target = os.readlink(sym_link)
                        if os.path.samefile(existing_link_target, u.storage_path):
                            remove_link = False
                    if remove_link:
                        # existing symlink is wrong, remove it
                        os.unlink(sym_link)
                dirpath = os.path.dirname(sym_link)
                if not os.path.exists(dirpath):
                    os.makedirs(dirpath)
                os.symlink(u.storage_path, sym_link)
            import_conduit.associate_unit(u)
        _LOG.info("%s units from %s have been associated to %s" % (len(units), source_repo.id, dest_repo.id))


    def remove_units(self, repo, units, remove_conduit):
        """
        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.content.plugins.data.Repository}

        @param units: list of objects describing the units to import in this call
        @type  units: list of L{pulp.server.content.plugins.data.Unit}

        @param remove_conduit: provides access to relevant Pulp functionality
        @type  remove_conduit: ?
        """
        _LOG.info("remove_units invoked for %s units" % (len(units)))
        for u in units:
            # Assuming Pulp will delete u.storage_path from filesystem
            sym_link = os.path.join(repo.working_dir, repo.id, u.unit_key["filename"])
            if os.path.lexists(sym_link):
                os.unlink(sym_link)
    # -- actions --------------------------------------------------------------

    def sync_repo(self, repo, sync_conduit, config):
        try:
            status, summary, details = self._sync_repo(repo, sync_conduit, config)
            if status:
                report = sync_conduit.build_success_report(summary, details)
            else:
                report = sync_conduit.build_failure_report(summary, details)
        except Exception, e:
            _LOG.error("Caught Exception: %s" % (e))
            summary = {}
            summary["error"] = str(e)
            report = sync_conduit.build_failure_report(summary, None)
        return report

    def _sync_repo(self, repo, sync_conduit, config):
        progress_status = {
                "metadata": {"state": "NOT_STARTED"},
                "content": {"state": "NOT_STARTED"},
                "errata": {"state": "NOT_STARTED", "num_errata":0}
                }
        def progress_callback(type_id, status):
            if type_id == "content":
                progress_status["metadata"]["state"] = "FINISHED"
                
            progress_status[type_id] = status
            sync_conduit.set_progress(progress_status)

        # sync rpms
        rpm_status, rpm_summary, rpm_details = importer_rpm._sync(repo, sync_conduit, config, progress_callback)
        progress_status["content"]["state"] = "FINISHED"
        sync_conduit.set_progress(progress_status)

        # sync errata
        errata_status, errata_summary, errata_details = errata._sync(repo, sync_conduit, config, progress_callback)
        progress_status["errata"]["state"] = "FINISHED"
        sync_conduit.set_progress(progress_status)

        summary = dict(rpm_summary.items() + errata_summary.items())
        details = dict(rpm_details.items() + errata_details.items())
        return (rpm_status and errata_status), summary, details

