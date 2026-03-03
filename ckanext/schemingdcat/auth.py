# encoding: utf-8
"""
Auth overrides for schemingdcat.

Replaces CKAN's default ``package_create`` and ``package_update`` auth
functions with versions that **skip the group-membership check**
(``_check_group_auth``).

CKAN core requires the acting user to hold ``manage_group`` on every
group listed in the dataset.  In portals that use scheming group fields
(``groups__0__id``, ``groups__1__id``, …), this prevents organisation
admins from tagging datasets with groups they do not personally manage.

These overrides remove that restriction while keeping every other
authorisation check (org ownership, collaborator, config permissions)
intact.
"""

from typing import Optional

import ckan.logic as logic
import ckan.authz as authz
import ckan.logic.auth as logic_auth
from ckan.common import _
from ckan.types import Context, DataDict, AuthResult

import logging

log = logging.getLogger(__name__)


@logic.auth_allow_anonymous_access
def schemingdcat_package_create(
    context: Context,
    data_dict: Optional[DataDict] = None,
) -> AuthResult:
    """Authorise package creation — without the group-membership gate."""

    user = context['user']

    if authz.auth_is_anon_user(context):
        check1 = all(authz.check_config_permission(p) for p in (
            'anon_create_dataset',
            'create_dataset_if_not_in_organization',
            'create_unowned_dataset',
        ))
    else:
        check1 = all(authz.check_config_permission(p) for p in (
            'create_dataset_if_not_in_organization',
            'create_unowned_dataset',
        )) or authz.has_user_permission_for_some_org(
            user, 'create_dataset')

    if not check1:
        return {
            'success': False,
            'msg': _('User %s not authorized to create packages') % user,
        }

    # NOTE: _check_group_auth intentionally omitted so that any
    # authenticated user who can create datasets may also assign them
    # to groups via scheming group fields.

    # Organisation-level check
    data_dict = data_dict or {}
    org_id = data_dict.get('owner_org')
    if org_id and not authz.has_user_permission_for_group_or_org(
            org_id, user, 'create_dataset'):
        return {
            'success': False,
            'msg': _(
                'User %s not authorized to add dataset to this organization'
            ) % user,
        }

    return {'success': True}


@logic.auth_allow_anonymous_access
def schemingdcat_package_update(
    context: Context,
    data_dict: DataDict,
) -> AuthResult:
    """Authorise package update — without the group-membership gate."""

    model = context['model']
    user = context.get('user')

    package = logic_auth.get_package_object(context, data_dict)
    if package.owner_org:
        check1 = authz.has_user_permission_for_group_or_org(
            package.owner_org, user, 'update_dataset')
    else:
        if authz.auth_is_anon_user(context):
            check1 = all(authz.check_config_permission(p) for p in (
                'anon_create_dataset',
                'create_dataset_if_not_in_organization',
                'create_unowned_dataset',
            ))
        else:
            check1 = all(authz.check_config_permission(p) for p in (
                'create_dataset_if_not_in_organization',
                'create_unowned_dataset',
            )) or authz.has_user_permission_for_some_org(
                user, 'create_dataset')

    if not check1:
        success = False
        if authz.check_config_permission('allow_dataset_collaborators'):
            user_obj = model.User.get(user)
            if user_obj:
                success = authz.user_is_collaborator_on_dataset(
                    user_obj.id, package.id, ['admin', 'editor'])
        if not success:
            return {
                'success': False,
                'msg': _('User %s not authorized to edit package %s') % (
                    str(user), package.id),
            }

    # NOTE: _check_group_auth intentionally omitted — same rationale as
    # schemingdcat_package_create above.

    return {'success': True}
