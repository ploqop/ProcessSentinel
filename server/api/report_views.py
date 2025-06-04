"""
Представления для работы с отчетами
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import datetime, timedelta
import json
from django.http import HttpResponse

from .models_extension import Report
from .serializers_extension import ReportSerializer
from .report_generator import ReportGenerator
from .audit_logger import log_event

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_report(request):
    """
    Генерирует новый отчет по указанным параметрам.
    
    Параметры запроса:
    - report_type: тип отчета (client_activity, policy_violations, commands_execution)
    - start_date: начальная дата отчета в формате ISO
    - end_date: конечная дата отчета в формате ISO
    - parameters: дополнительные параметры для отчета (опционально)
    """
    try:
        report_type = request.data.get('report_type')
        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')
        parameters = request.data.get('parameters', {})
        
        if not report_type or not start_date_str or not end_date_str:
            return Response(
                {"error": "report_type, start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем тип отчета
        if report_type not in [r[0] for r in Report.REPORT_TYPES]:
            return Response(
                {"error": f"Invalid report_type. Available types: {[r[0] for r in Report.REPORT_TYPES]}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start_date = datetime.fromisoformat(start_date_str)
            end_date = datetime.fromisoformat(end_date_str)
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        manager = request.user.managerprofile
        
        # Генерируем отчет в зависимости от типа
        if report_type == 'client_activity':
            report = ReportGenerator.generate_client_activity_report(
                manager, start_date, end_date, parameters
            )
        elif report_type == 'policy_violations':
            report = ReportGenerator.generate_policy_violations_report(
                manager, start_date, end_date, parameters
            )
        elif report_type == 'commands_execution':
            report = ReportGenerator.generate_commands_execution_report(
                manager, start_date, end_date, parameters
            )
        else:
            # Этот блок не должен выполниться, т.к. мы уже проверили тип отчета выше
            return Response(
                {"error": f"Report type {report_type} not implemented yet"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Логируем событие
        log_event('report_generated', None, manager, 
                 {'report_id': str(report.id), 'report_type': report_type}, 
                 request)
        
        # Возвращаем сериализованный отчет
        serializer = ReportSerializer(report)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {"error": f"Error generating report: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_reports(request):
    """
    Возвращает список отчетов менеджера.
    
    Параметры запроса:
    - report_type: фильтр по типу отчета (опционально)
    - limit: ограничение количества отчетов (опционально, по умолчанию 20)
    """
    try:
        report_type = request.query_params.get('report_type')
        limit = int(request.query_params.get('limit', 20))
        
        manager = request.user.managerprofile
        
        # Фильтруем отчеты
        reports = Report.objects.filter(manager=manager)
        if report_type:
            reports = reports.filter(report_type=report_type)
        
        # Ограничиваем количество и сортируем по дате создания
        reports = reports.order_by('-created_at')[:limit]
        
        # Сериализуем и возвращаем
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {"error": f"Error getting reports: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_report(request, report_id):
    """
    Возвращает детали конкретного отчета.
    """
    try:
        manager = request.user.managerprofile
        
        try:
            report = Report.objects.get(id=report_id, manager=manager)
        except Report.DoesNotExist:
            return Response(
                {"error": "Report not found or access denied"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ReportSerializer(report)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {"error": f"Error getting report: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_report(request, report_id, format='json'):
    """
    Экспортирует отчет в указанном формате (json или csv).
    """
    try:
        manager = request.user.managerprofile
        
        try:
            report = Report.objects.get(id=report_id, manager=manager)
        except Report.DoesNotExist:
            return Response(
                {"error": "Report not found or access denied"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if format == 'json':
            # Экспорт в JSON
            response = HttpResponse(json.dumps(report.result, indent=2), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="{report.report_type}_{report.id}.json"'
            return response
        elif format == 'csv':
            # Экспорт в CSV
            # Здесь нужна более сложная логика для преобразования JSON в CSV
            # в зависимости от типа отчета
            return Response(
                {"error": "CSV export not implemented yet"},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        else:
            return Response(
                {"error": f"Unsupported format: {format}. Available formats: json, csv"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
    except Exception as e:
        return Response(
            {"error": f"Error exporting report: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_audit_logs(request):
    """
    Возвращает аудит-логи с возможностью фильтрации.
    
    Параметры запроса:
    - client_uuid: фильтр по клиенту (опционально)
    - log_type: фильтр по типу лога (опционально)
    - start_date: начальная дата в формате ISO (опционально)
    - end_date: конечная дата в формате ISO (опционально)
    - limit: ограничение количества логов (опционально, по умолчанию 100)
    """
    from .models_extension import AuditLog
    from .serializers_extension import AuditLogSerializer
    
    try:
        client_uuid = request.query_params.get('client_uuid')
        log_type = request.query_params.get('log_type')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        limit = int(request.query_params.get('limit', 100))
        
        manager = request.user.managerprofile
        
        # Базовый запрос: все логи для клиентов менеджера
        logs = AuditLog.objects.filter(client__manager=manager)
        
        # Применяем фильтры
        if client_uuid:
            logs = logs.filter(client__uuid=client_uuid)
        
        if log_type:
            logs = logs.filter(log_type=log_type)
        
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str)
                logs = logs.filter(timestamp__gte=start_date)
            except ValueError:
                return Response(
                    {"error": "Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str)
                logs = logs.filter(timestamp__lte=end_date)
            except ValueError:
                return Response(
                    {"error": "Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Ограничиваем количество и сортируем по времени
        logs = logs.order_by('-timestamp')[:limit]
        
        # Сериализуем и возвращаем
        serializer = AuditLogSerializer(logs, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {"error": f"Error getting audit logs: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )