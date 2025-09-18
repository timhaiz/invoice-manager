from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError


class Command(BaseCommand):
    help = '创建默认超级用户账户 (用户名: admin, 密码: admin123)'

    def handle(self, *args, **options):
        User = get_user_model()
        
        try:
            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='admin123'
                )
                self.stdout.write(
                    self.style.SUCCESS('默认超级用户已创建成功!')
                )
                self.stdout.write(
                    self.style.SUCCESS('用户名: admin')
                )
                self.stdout.write(
                    self.style.SUCCESS('密码: admin123')
                )
                self.stdout.write(
                    self.style.WARNING('请登录后台后立即修改密码!')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('超级用户 "admin" 已存在，跳过创建。')
                )
        except IntegrityError as e:
            self.stdout.write(
                self.style.ERROR(f'创建超级用户时出现数据库完整性错误: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'创建超级用户失败: {e}')
            )