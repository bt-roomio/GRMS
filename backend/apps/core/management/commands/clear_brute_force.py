"""
Manage brute force protection counters.

Examples:
    ./manage.py clear_brute_force --email user@example.com
    ./manage.py clear_brute_force --email user@example.com --show
    ./manage.py clear_brute_force --email user@example.com --ip 1.2.3.4
    ./manage.py clear_brute_force --ip 1.2.3.4 --hard-block
    ./manage.py clear_brute_force --ip 1.2.3.4 --unblock
"""

from django.core.management.base import BaseCommand, CommandError

from core.utils.brute_force import get_lock_status, hard_block_key, security_cache, unlock_account


class Command(BaseCommand):
    help = "Show or reset brute force protection counters"

    def add_arguments(self, parser):
        parser.add_argument("--email", help="User email (case-insensitive)")
        parser.add_argument("--ip", action="append", help="Restrict to a specific IP (repeatable)")
        parser.add_argument("--show", action="store_true", help="Only show the state, delete nothing")
        parser.add_argument("--hard-block", action="store_true", help="Ban the IP permanently")
        parser.add_argument("--unblock", action="store_true", help="Lift a permanent IP ban")

    def handle(self, *args, **options):
        ips = options.get("ip")
        email = options.get("email")

        if options["hard_block"] and options["unblock"]:
            raise CommandError("--hard-block and --unblock are mutually exclusive")

        if options["hard_block"] or options["unblock"]:
            if not ips:
                raise CommandError("--hard-block/--unblock require at least one --ip")
            for ip in ips:
                if options["hard_block"]:
                    security_cache.set(hard_block_key(ip), True, None)
                    self.stdout.write(self.style.WARNING(f"IP {ip} permanently blocked"))
                else:
                    security_cache.delete(hard_block_key(ip))
                    self.stdout.write(self.style.SUCCESS(f"Permanent block lifted for {ip}"))
            return

        if not email:
            raise CommandError("--email is required unless --hard-block/--unblock is given")

        status = get_lock_status(email)
        self.stdout.write(f"email: {status['email']}")
        self.stdout.write(f"known IPs: {', '.join(status['known_ips']) or '-'}")
        self.stdout.write(f"locked: {'yes' if status['is_locked'] else 'no'}")
        for lock in status["locks"]:
            left = f"{lock['seconds_left']}s" if lock["seconds_left"] is not None else "indefinitely"
            self.stdout.write(f"  {lock['ip']} {lock['endpoint'] or '(whole IP)'} - {lock['reason']}, {left} left")

        if options["show"]:
            return

        result = unlock_account(email, ips=ips)
        self.stdout.write(
            self.style.SUCCESS(
                f"Unlocked {result['email']}: cleared {result['cleared_keys']} keys "
                f"for IPs {', '.join(result['cleared_ips']) or '-'}"
            )
        )
