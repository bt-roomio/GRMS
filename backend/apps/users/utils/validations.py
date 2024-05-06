from rest_framework.exceptions import ValidationError


def mail_fields(fields):
    if not fields.get('smtpHost') or not fields.get('smtpPort') or not fields.get('username') or not fields.get(
            'password'):
        raise ValidationError(
            {'detail': 'Configurations must include "smtpHost" and "smtpPort" and "username" and "password"'})

    return (fields.get('smtpHost'), fields.get('smtpPort'), fields.get('username'), fields.get('password'),
            fields.get('enableTls'))
