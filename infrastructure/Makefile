dev-workspace:
	terraform workspace select default
dev-init:
	terraform init -backend-config="dev.conf"
dev-plan:
	terraform plan -var-file="dev.tfvars"
dev-apply:
	terraform apply -var-file="dev.tfvars"
dev-apply-deploy:
	terraform apply -var-file="dev.tfvars" --auto-approve
