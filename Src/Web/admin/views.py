import math
import time
from flask import request
from flask_security import current_user

import flask_admin
from flask import Flask, jsonify, url_for, redirect, render_template, request
from flask_admin.contrib.mongoengine import ModelView
from flask_admin import expose

from Notify.NotifyManager import dispatch_event, NOTIFY_EVENT

# project import
from Config import ConfigManager
from Manager.ProxyManager import proxy_manager

CUSTOM_COLUMN_FORMAT = {
    "type" : [
        "未知",
        "透明",
        "匿名",
    ],
    "https" : [
        "未知",
        "开启",
        "关闭",
    ],
    "last_status": [
        "未知",
        "成功",
        "失败"
    ]
}

def ElapseTimeFormat(all_time):
    day = 24*60*60
    hour = 60*60
    min = 60
    if all_time <60:        
        return  "%d sec"%math.ceil(all_time)
    elif  all_time > day:
        days = divmod(all_time,day) 
        return "%d days, %s"%(int(days[0]),ElapseTimeFormat(days[1]))
    elif all_time > hour:
        hours = divmod(all_time,hour)
        return '%d hours, %s'%(int(hours[0]),ElapseTimeFormat(hours[1]))
    else:
        mins = divmod(all_time,min)
        return "%d mins, %d sec"%(int(mins[0]),math.ceil(mins[1]))

def LastSuccTimeFormat(last_time):
    if last_time:
        result = ElapseTimeFormat(int(time.time() - last_time))
    else:
        result = 0

    return result

def TimeStampFormat(timeStamp):
    time_object = time.localtime(timeStamp)
    result = time.strftime("%Y-%m-%d %H:%M:%S", time_object)
    return result

def PercentFormat(cur, total):
    if total == 0:
        percent = 0
    else:
        percent = float(cur / total * 100)
    result = "%d(%.2f%%)" % (cur, percent)

    return result

class ProxyView(ModelView):
    name = "ProxyPool"

    column_list = ("proxy", "succ", "total", "keep_succ", "type", "https", "last_status", "last_succ_time", "region_list")
    can_create = False
    column_formatters = dict(
        type=lambda v, c, m, p: CUSTOM_COLUMN_FORMAT[p][m.type],
        https=lambda v, c, m, p: CUSTOM_COLUMN_FORMAT[p][m.https],
        last_status=lambda v, c, m, p: CUSTOM_COLUMN_FORMAT[p][m.last_status],
        last_succ_time=lambda v, c, m, p: LastSuccTimeFormat(m.last_succ_time),
        succ=lambda v, c, m, p: PercentFormat(m.succ, m.total),
    )

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('superuser'):
            return True

        return False

    def _handle_view(self, name, **kwargs):
        if current_user.is_authenticated:
            pass
        else:
            return redirect(url_for('security.login', next=request.url))

class SettingView(ModelView):
    name="Setting"

    can_create = False
    can_delete = False
    can_view_details = True
    column_searchable_list = ['setting_name']
    column_editable_list = [ "setting_value", "setting_state"]

    def is_accessible(self):
        result = None
        if not current_user.is_active or not current_user.is_authenticated:
            result = False

        if current_user.has_role('superuser'):
            result = True

        return result

    def _handle_view(self, name, **kwargs):
        if current_user.is_authenticated:
            pass
        else:
            return redirect(url_for('security.login', next=request.url))

    def after_model_change(self, form, model, is_created):
        kwargs = dict(
            event_name=model.setting_name,
            event_data=dict(
                job_id=model.setting_name
            )
        )
        dispatch_event(NOTIFY_EVENT["AFTER_SETTING_CHANGE"], **kwargs)

class FetcherView(ModelView):
    name="Fethers"

    column_list = ("name", "host", "succ", "fail", "skip", "total", "status", "interval", "next_fetch_time")
    can_create = False
    can_delete = False
    can_view_details = True
    column_searchable_list = ['name']
    column_editable_list = [ "status", "interval"]
    column_formatters = dict(
        succ=lambda v, c, m, p: PercentFormat(m.succ, m.total),
        fail=lambda v, c, m, p: PercentFormat(m.fail, m.total),
        skip=lambda v, c, m, p: PercentFormat(m.skip, m.total),
        next_fetch_time=lambda v, c, m, p: TimeStampFormat(m.next_fetch_time),
    )

    def is_accessible(self):
        result = None
        if not current_user.is_active or not current_user.is_authenticated:
            result = False

        if current_user.has_role('superuser'):
            result = True

        return result

    def _handle_view(self, name, **kwargs):
        if current_user.is_authenticated:
            pass
        else:
            return redirect(url_for('security.login', next=request.url))

class ProxyPoolAdminIndexView(flask_admin.AdminIndexView):

    @expose()
    def index(self):
        if not current_user.is_authenticated:
            return redirect(url_for('security.login'))
        return super(ProxyPoolAdminIndexView, self).index()
