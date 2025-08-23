from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView

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
            public_space_id=params.get("public_space"),
            user_id=params.get("user"),
            card_num=params.get("card_num"),
            tenant_id=tenant_id,
        )

        if not logs.exists():
            return JsonResponse({"detail": "No logs found for given filters."}, status=404)

        wb = Workbook()
        ws = wb.active
        ws.title = "Card Logs"

        # --- Headers ---
        headers = [
            "Card Number", "Event Timestamp", "Access Group",
            "Device", "Spaces", "User Type", "User Name", "Created At"
        ]
        ws.append(headers)

        header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")

        for cell in ws[1]:
            cell.font = Font(bold=True, size=14, color="000000")
            cell.fill = header_fill
            cell.alignment = header_alignment

        # --- Data rows ---
        data_alignment = Alignment(horizontal="center", vertical="center")

        for log in logs:
            if log.staff:
                user_type, user_name = "Staff", log.staff.get_name()
            elif log.guest:
                user_type, user_name = "Guest", log.guest.get_name()
            else:
                user_type, user_name = "", ""

            spaces = get_space(log.device.id)
            space_field = ", ".join(spaces) if spaces else ""

            row = [
                log.number,
                log.event_ts.strftime("%Y-%m-%d %H:%M:%S"),
                log.get_access_group_display(),
                str(log.device),
                space_field,
                user_type,
                user_name,
                log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ]
            ws.append(row)

            # Center align the just-added row
            for cell in ws[ws.max_row]:
                cell.alignment = data_alignment

        # --- Auto-adjust column widths ---
        for col_cells in ws.columns:
            max_length = 0
            col_letter = get_column_letter(col_cells[0].column)
            for cell in col_cells:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except Exception:
                    pass
            adjusted_width = max_length + 1  # tighter spacing
            if adjusted_width < 20:          # min width for readability
                adjusted_width = 20
            ws.column_dimensions[col_letter].width = adjusted_width

        # --- Response ---
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="card_logs.xlsx"'
        wb.save(response)

        response["X-Message"] = "CardLogs file sent successfully"
        return response
