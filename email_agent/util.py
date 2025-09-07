def refine_input_prompt(email_data: dict, existing_labels: list[str]):
    return f"""
Email:
- ID: {email_data['id']}
- Subject: {email_data['subject']}
- From: {email_data['from']}
- Date: {email_data['date']}
- Text Snipet: {email_data['snipet']}
- Attachments: { ', '.join([
                f"File Name: {attachment['filename']} - Mime Type: {attachment['mimeType']} - Size: {attachment['size']}"
                for attachment in email_data["attachments"]
            ]) if len(email_data['attachments']) > 0 else "No attachments" }
Existing Labels: {", ".join(existing_labels)}
Assign a Label to the above email in AT MOST 3 words. Answer with the Label ALONE and NOTHING ELSE.
"""