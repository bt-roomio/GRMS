from django.urls import path

from alarms.views.alarm import (
    AlarmAckView,
    AlarmAssignView,
    AlarmBulkAckView,
    AlarmBulkClearView,
    AlarmClearView,
    AlarmCommentDetailView,
    AlarmCommentView,
    AlarmDetailView,
    AlarmListView,
    AlarmSummaryView,
    AlarmTypeView,
    AvailableKeysView,
)
from alarms.views.rule import (
    AlarmRuleBulkView,
    AlarmRuleDetailView,
    AlarmRuleListView,
    AlarmRulePreviewView,
    AlarmRuleTemplateView,
)

urlpatterns = [
    path("", AlarmListView.as_view(), name="alarm-list"),
    path("summary/", AlarmSummaryView.as_view(), name="alarm-summary"),
    path("types/", AlarmTypeView.as_view(), name="alarm-types"),
    path("available-keys/", AvailableKeysView.as_view(), name="alarm-available-keys"),
    path("rules/", AlarmRuleListView.as_view(), name="rule-list"),
    path("rules/bulk/", AlarmRuleBulkView.as_view(), name="rule-bulk"),
    path("rule-templates/", AlarmRuleTemplateView.as_view(), name="rule-templates"),
    path("rules/preview/", AlarmRulePreviewView.as_view(), name="rule-preview"),
    path("rules/<uuid:pk>/", AlarmRuleDetailView.as_view(), name="rule-detail"),
    path("bulk/ack/", AlarmBulkAckView.as_view(), name="alarm-bulk-ack"),
    path("bulk/clear/", AlarmBulkClearView.as_view(), name="alarm-bulk-clear"),
    path("<uuid:pk>/", AlarmDetailView.as_view(), name="alarm-detail"),
    path("<uuid:pk>/ack/", AlarmAckView.as_view(), name="alarm-ack"),
    path("<uuid:pk>/clear/", AlarmClearView.as_view(), name="alarm-clear"),
    path("<uuid:pk>/assign/", AlarmAssignView.as_view(), name="alarm-assign"),
    path("<uuid:pk>/comments/", AlarmCommentView.as_view(), name="alarm-comments"),
    path(
        "<uuid:pk>/comments/<uuid:comment_pk>/",
        AlarmCommentDetailView.as_view(),
        name="alarm-comment-detail",
    ),
]
