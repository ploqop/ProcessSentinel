"""
Генератор отчетов для системы аудита
"""
import logging
from datetime import datetime, timedelta
from django.db.models import Count, F, Q
from .models import ClientAgent, Command, Policy
from .models_extension import AuditLog, Report

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Класс для генерации различных типов отчетов"""
    
    @staticmethod
    def generate_client_activity_report(manager, start_date, end_date, parameters=None):
        """
        Генерирует отчет по активности клиентов
        
        Args:
            manager: ManagerProfile объект менеджера
            start_date: Начальная дата для отчета
            end_date: Конечная дата для отчета
            parameters: Дополнительные параметры для отчета
            
        Returns:
            Report: Созданный отчет
        """
        if parameters is None:
            parameters = {}
            
        try:
            # Получаем клиентов менеджера
            clients = ClientAgent.objects.filter(manager=manager)
            
            # Собираем данные активности по логам
            activity_data = []
            for client in clients:
                # Количество сигналов активности
                heartbeats = AuditLog.objects.filter(
                    client=client,
                    log_type='heartbeat',
                    timestamp__gte=start_date,
                    timestamp__lte=end_date
                ).count()
                
                # Количество подключений
                connections = AuditLog.objects.filter(
                    client=client,
                    log_type='client_connection',
                    timestamp__gte=start_date,
                    timestamp__lte=end_date
                ).count()
                
                # Количество нарушений политик
                violations = AuditLog.objects.filter(
                    client=client,
                    log_type='policy_violation',
                    timestamp__gte=start_date,
                    timestamp__lte=end_date
                ).count()
                
                # Время последней активности
                last_activity = AuditLog.objects.filter(
                    client=client,
                    timestamp__gte=start_date,
                    timestamp__lte=end_date
                ).order_by('-timestamp').first()
                
                activity_data.append({
                    'client_uuid': str(client.uuid),
                    'client_name': client.name,
                    'heartbeats': heartbeats,
                    'connections': connections,
                    'violations': violations,
                    'last_activity': last_activity.timestamp.isoformat() if last_activity else None,
                    'is_online': client.is_online
                })
            
            # Суммарная статистика
            summary = {
                'total_clients': len(clients),
                'active_clients': sum(1 for d in activity_data if d['heartbeats'] > 0),
                'online_clients': sum(1 for d in activity_data if d['is_online']),
                'total_violations': sum(d['violations'] for d in activity_data),
                'total_connections': sum(d['connections'] for d in activity_data)
            }
            
            # Создаем результат отчета
            result = {
                'summary': summary,
                'clients': activity_data
            }
            
            # Сохраняем отчет
            report = Report.objects.create(
                manager=manager,
                report_type='client_activity',
                parameters=parameters,
                result=result,
                start_date=start_date,
                end_date=end_date
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating client activity report: {str(e)}")
            raise
            
    @staticmethod
    def generate_policy_violations_report(manager, start_date, end_date, parameters=None):
        """
        Генерирует отчет по нарушениям политик безопасности
        
        Args:
            manager: ManagerProfile объект менеджера
            start_date: Начальная дата для отчета
            end_date: Конечная дата для отчета
            parameters: Дополнительные параметры для отчета
            
        Returns:
            Report: Созданный отчет
        """
        if parameters is None:
            parameters = {}
        
        try:
            # Получаем все нарушения политик для клиентов менеджера
            violations = AuditLog.objects.filter(
                client__manager=manager,
                log_type='policy_violation',
                timestamp__gte=start_date,
                timestamp__lte=end_date
            ).order_by('-timestamp')
            
            # Группируем нарушения по процессам
            process_violations = {}
            for violation in violations:
                process_name = violation.details.get('process_name', 'Unknown')
                if process_name not in process_violations:
                    process_violations[process_name] = 0
                process_violations[process_name] += 1
                
            # Группируем нарушения по клиентам
            client_violations = {}
            for violation in violations:
                client_name = violation.client.name if violation.client else 'Unknown'
                client_uuid = str(violation.client.uuid) if violation.client else 'Unknown'
                
                if client_uuid not in client_violations:
                    client_violations[client_uuid] = {
                        'client_name': client_name,
                        'count': 0,
                        'processes': {}
                    }
                
                client_violations[client_uuid]['count'] += 1
                
                process_name = violation.details.get('process_name', 'Unknown')
                if process_name not in client_violations[client_uuid]['processes']:
                    client_violations[client_uuid]['processes'][process_name] = 0
                client_violations[client_uuid]['processes'][process_name] += 1
            
            # Детали каждого нарушения
            violation_details = []
            for violation in violations:
                violation_details.append({
                    'id': str(violation.id),
                    'client_name': violation.client.name if violation.client else 'Unknown',
                    'client_uuid': str(violation.client.uuid) if violation.client else 'Unknown',
                    'timestamp': violation.timestamp.isoformat(),
                    'process_name': violation.details.get('process_name', 'Unknown'),
                    'process_id': violation.details.get('process_id', 'Unknown'),
                    'details': violation.details
                })
            
            # Создаем результат отчета
            result = {
                'summary': {
                    'total_violations': violations.count(),
                    'unique_processes': len(process_violations),
                    'affected_clients': len(client_violations)
                },
                'by_process': [{'process': k, 'count': v} for k, v in process_violations.items()],
                'by_client': [{'client_uuid': k, 'client_name': v['client_name'], 
                             'count': v['count'], 'processes': v['processes']} 
                            for k, v in client_violations.items()],
                'violations': violation_details
            }
            
            # Сохраняем отчет
            report = Report.objects.create(
                manager=manager,
                report_type='policy_violations',
                parameters=parameters,
                result=result,
                start_date=start_date,
                end_date=end_date
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating policy violations report: {str(e)}")
            raise
            
    @staticmethod
    def generate_commands_execution_report(manager, start_date, end_date, parameters=None):
        """
        Генерирует отчет по выполнению команд
        
        Args:
            manager: ManagerProfile объект менеджера
            start_date: Начальная дата для отчета
            end_date: Конечная дата для отчета
            parameters: Дополнительные параметры для отчета
            
        Returns:
            Report: Созданный отчет
        """
        if parameters is None:
            parameters = {}
        
        try:
            # Получаем все команды для клиентов менеджера
            commands = Command.objects.filter(
                client__manager=manager,
                sent_at__gte=start_date,
                sent_at__lte=end_date
            ).order_by('-sent_at')
            
            # Группируем команды по типам
            command_types = {}
            for cmd in commands:
                if cmd.command_type not in command_types:
                    command_types[cmd.command_type] = {
                        'total': 0,
                        'executed': 0,
                        'failed': 0
                    }
                command_types[cmd.command_type]['total'] += 1
                if cmd.executed:
                    command_types[cmd.command_type]['executed'] += 1
                else:
                    command_types[cmd.command_type]['failed'] += 1
            
            # Группируем команды по клиентам
            client_commands = {}
            for cmd in commands:
                client_name = cmd.client.name if cmd.client else 'Unknown'
                client_uuid = str(cmd.client.uuid) if cmd.client else 'Unknown'
                
                if client_uuid not in client_commands:
                    client_commands[client_uuid] = {
                        'client_name': client_name,
                        'total': 0,
                        'executed': 0,
                        'failed': 0,
                        'by_type': {}
                    }
                
                client_commands[client_uuid]['total'] += 1
                if cmd.executed:
                    client_commands[client_uuid]['executed'] += 1
                else:
                    client_commands[client_uuid]['failed'] += 1
                
                if cmd.command_type not in client_commands[client_uuid]['by_type']:
                    client_commands[client_uuid]['by_type'][cmd.command_type] = {
                        'total': 0,
                        'executed': 0,
                        'failed': 0
                    }
                
                client_commands[client_uuid]['by_type'][cmd.command_type]['total'] += 1
                if cmd.executed:
                    client_commands[client_uuid]['by_type'][cmd.command_type]['executed'] += 1
                else:
                    client_commands[client_uuid]['by_type'][cmd.command_type]['failed'] += 1
            
            # Детали каждой команды
            command_details = []
            for cmd in commands:
                command_details.append({
                    'id': str(cmd.id),
                    'client_name': cmd.client.name if cmd.client else 'Unknown',
                    'client_uuid': str(cmd.client.uuid) if cmd.client else 'Unknown',
                    'command_type': cmd.command_type,
                    'parameters': cmd.parameters,
                    'sent_at': cmd.sent_at.isoformat(),
                    'executed': cmd.executed,
                    'result': cmd.result
                })
            
            # Создаем результат отчета
            result = {
                'summary': {
                    'total_commands': commands.count(),
                    'executed_commands': sum(1 for cmd in commands if cmd.executed),
                    'failed_commands': sum(1 for cmd in commands if not cmd.executed),
                    'unique_clients': len(client_commands)
                },
                'by_type': command_types,
                'by_client': [{'client_uuid': k, 'client_name': v['client_name'], 
                             'total': v['total'], 'executed': v['executed'], 
                             'failed': v['failed'], 'by_type': v['by_type']} 
                            for k, v in client_commands.items()],
                'commands': command_details
            }
            
            # Сохраняем отчет
            report = Report.objects.create(
                manager=manager,
                report_type='commands_execution',
                parameters=parameters,
                result=result,
                start_date=start_date,
                end_date=end_date
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating commands execution report: {str(e)}")
            raise