FROM python:3.9-slim-buster

LABEL "com.github.actions.name"="Preview Environment on ECS GitHub Action"
LABEL "com.github.actions.description"="This is a github actions to provision preview environment on AWS ECS."
LABEL "com.github.actions.icon"="airplay"
LABEL "com.github.actions.color"="green"

WORKDIR /

COPY . .

RUN apt-get update && apt-get install -y curl zip \
  && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
  && unzip awscliv2.zip && ./aws/install && rm -rf awscliv2.zip \
  && pip install --no-cache-dir -r requirements.txt \
  && chmod +x entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
