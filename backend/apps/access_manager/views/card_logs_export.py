import openpyxl
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from openpyxl.styles import Font
from access_manager.models import CardLog
from access_manager.serializers.card_log import CardLogFilterParams
from access_manager.swagger.card_log_export import swagger_export_card_logs
from main.utils.get_device_space import get_space


class ExportCardLogsExcelView(APIView):
    @swagger_export_card_logs()
    def post(self, request, *args, **kwargs):
        params = CardLogFilterParams.check(request.data)
        tenant_id = request.user.tenant_id

        logs = CardLog.objects.select_related("staff", "guest", "device").list(
            filters=params.get("filters", {}),
            device_ids=params.get("device_ids", []),
            sort_by=params.get("sort_by", ["-event_ts"]),
            room_id=params.get("room"),
            user_id=params.get("user"),
            card_num=params.get("card_num"),
            tenant_id=tenant_id)

        if not logs.exists():
            return JsonResponse({"detail": "No logs found for given filters."}, status=404)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Card Logs"

        ws.append([
            "Card Number", "Event Timestamp", "Access Group",
            "Device", "Spaces", "User Type", "User Name", "Created At"
        ])
        for cell in ws[1]:
            cell.font = Font(bold=True, size=14)

        for log in logs:
            if log.staff:
                user_type, user_name = "Staff", log.staff.get_name()
            elif log.guest:
                user_type, user_name = "Guest", log.guest.get_name()
            else:
                user_type, user_name = "", ""

            spaces = get_space(log.device.id)
            space_field = ", ".join(spaces) if spaces else ""

            ws.append([
                log.number,
                log.event_ts.strftime("%Y-%m-%d %H:%M:%S"),
                log.get_access_group_display(),
                str(log.device),
                space_field,
                user_type,
                user_name,
                log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="card_logs.xlsx"'
        wb.save(response)

        response["X-Message"] = "CardLogs file sent successfully"
        return response
