import sys
import os
import random
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal
from src.models import Job, JobStatus

def add_mock_data():
    jobs = [
        {
            "title": "Senior Site Reliability Engineer",
            "company": "CloudScale Solutions",
            "location": "Remote, US",
            "url": "https://example.com/jobs/sre-1",
            "description": """
            About the Role:
            We are looking for a Senior SRE to join our infrastructure team. You will be responsible for the reliability, scalability, and performance of our global cloud platform.
            
            Key Responsibilities:
            - Manage and scale Kubernetes clusters on AWS (EKS).
            - Implement and maintain CI/CD pipelines using GitHub Actions.
            - Write Infrastructure as Code (IaC) using Terraform.
            - Monitor system health using Prometheus and Grafana.
            - Participate in an on-call rotation and lead incident response.
            
            Requirements:
            - 5+ years of experience in SRE or DevOps roles.
            - Strong expertise in Kubernetes and Docker.
            - Proficient in Python or Go for automation.
            - Experience with AWS services (EC2, S3, RDS, IAM).
            - Solid understanding of Linux networking and internals.
            """
        },
        {
            "title": "DevOps Engineer (L3)",
            "company": "FinTech Innovators",
            "location": "Bangalore, India",
            "url": "https://example.com/jobs/devops-india",
            "description": """
            FinTech Innovators is seeking a DevOps Engineer to automate our financial trading platform.
            
            What You'll Do:
            - Automate application deployments to Azure.
            - Manage Jenkins pipelines and transition to GitLab CI.
            - Support developers with containerization strategies.
            - Optimize SQL database performance and scaling.
            
            Skills Needed:
            - Experience with Azure Cloud.
            - Automation with Ansible and Bash.
            - Knowledge of monitoring tools like New Relic.
            - Experience in a high-compliance/regulated environment is a plus.
            """
        },
        {
            "title": "Lead Infrastructure Engineer",
            "company": "Global Retail Corp",
            "location": "Hyderabad, India",
            "url": "https://example.com/jobs/infra-lead",
            "description": """
            Join us as an Infrastructure Lead to oversee our transition to a hybrid-cloud environment.
            
            Responsibilities:
            - Lead a team of 4 engineers managing on-prem and GCP resources.
            - Standardize IaC practices across the organization.
            - Focus on cost optimization and security hardening.
            - Mentor junior engineers.
            
            Required:
            - 8+ years of infrastructure experience.
            - Strong GCP experience (GKE, Cloud Functions).
            - Leadership experience.
            - Expertise in Terraform and Python.
            """
        }
    ]

    db = SessionLocal()
    try:
        new_count = 0
        for job_data in jobs:
            # Check if exists to avoid duplicates on multiple runs
            ext_id = f"mock_{job_data['title'].replace(' ', '_')}_{job_data['company'].replace(' ', '_')}"
            existing = db.query(Job).filter(Job.job_id_external == ext_id).first()
            
            if not existing:
                job = Job(
                    job_id_external=ext_id,
                    title=job_data["title"],
                    company=job_data["company"],
                    location=job_data["location"],
                    url=job_data["url"],
                    description=job_data["description"],
                    source="mock",
                    status=JobStatus.NEW,
                    posted_date=datetime.now()
                )
                db.add(job)
                new_count += 1
        
        db.commit()
        print(f"✅ Successfully added {new_count} mock jobs for testing.")
    except Exception as e:
        print(f"❌ Failed to add mock data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_mock_data()
