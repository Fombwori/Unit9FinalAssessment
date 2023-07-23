# myapp/management/commands/run_theharvester.py

from django.core.management.base import BaseCommand
import subprocess

class Command(BaseCommand):
    help = 'Run TheHarvester to gather OSINT information'

    def handle(self, *args, **options):
        domain = 'example.com'  # Replace with your web application's domain
        output_file = '/path/to/output.txt'  # Replace with the desired output file

        # Run TheHarvester command as a subprocess
        command = f'theharvester -d {domain} -b all -f {output_file}'
        subprocess.run(command, shell=True)

        self.stdout.write(self.style.SUCCESS('TheHarvester successfully executed.'))
