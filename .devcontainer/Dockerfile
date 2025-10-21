FROM mcr.microsoft.com/devcontainers/base:ubuntu

ARG TARGETARCH
ENV TARGETARCH=${TARGETARCH}

ARG ASDF_VERSION
COPY .tool-versions.asdf /tmp/.tool-versions.asdf

# Add amd64 architecture if on arm64
RUN if [ "$TARGETARCH" == "arm64" ] || [ "$TARGETARCH" == "aarch64" ]; then dpkg --add-architecture amd64; fi

# Install system dependencies
RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y dist-upgrade \
    && apt-get -y install --no-install-recommends htop vim curl git build-essential \
    libffi-dev libssl-dev libxml2-dev libxslt1-dev libjpeg8-dev libbz2-dev \
    zlib1g-dev unixodbc unixodbc-dev libsecret-1-0 libsecret-1-dev libsqlite3-dev \
    jq apt-transport-https ca-certificates gnupg-agent \
    software-properties-common bash-completion python3-pip make libbz2-dev \
    libreadline-dev libsqlite3-dev wget llvm libncurses5-dev libncursesw5-dev \
    xz-utils tk-dev liblzma-dev netcat-openbsd libyaml-dev

# Install aws stuff
RUN if [ "$TARGETARCH" = "arm64" ] || [ "$TARGETARCH" == "aarch64" ]; then \
      wget -O /tmp/awscliv2.zip "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip"; \
    else \
      wget -O /tmp/awscliv2.zip "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip"; \
    fi && \
    unzip /tmp/awscliv2.zip -d /tmp/aws-cli && \
    /tmp/aws-cli/aws/install && \
    rm /tmp/awscliv2.zip && rm -rf /tmp/aws-cli

RUN if [ "$TARGETARCH" = "arm64" ] || [ "$TARGETARCH" == "aarch64" ]; then \
      wget -O /tmp/aws-sam-cli.zip "https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-arm64.zip"; \
    else \
      wget -O /tmp/aws-sam-cli.zip "https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip"; \
    fi && \
    unzip /tmp/aws-sam-cli.zip -d /tmp/aws-sam-cli && \
    /tmp/aws-sam-cli/install && \
    rm /tmp/aws-sam-cli.zip && rm -rf /tmp/aws-sam-cli

# Install ASDF
RUN ASDF_VERSION=$(awk '!/^#/ && NF {print $1; exit}' /tmp/.tool-versions.asdf) && \
    if [ "$TARGETARCH" = "arm64" ] || [ "$TARGETARCH" == "aarch64" ]; then \
      wget -O /tmp/asdf.tar.gz "https://github.com/asdf-vm/asdf/releases/download/v${ASDF_VERSION}/asdf-v${ASDF_VERSION}-linux-arm64.tar.gz"; \
    else \
      wget -O /tmp/asdf.tar.gz "https://github.com/asdf-vm/asdf/releases/download/v${ASDF_VERSION}/asdf-v${ASDF_VERSION}-linux-amd64.tar.gz"; \
    fi && \
    tar -xzf /tmp/asdf.tar.gz -C /tmp && \
    mkdir -p /usr/bin && \
    mv /tmp/asdf /usr/bin/asdf && \
    chmod +x /usr/bin/asdf && \
    rm -rf /tmp/asdf.tar.gz

USER vscode

RUN mkdir -p /home/vscode/.asdf/shims /home/vscode/.asdf/installs

ENV PATH="/home/vscode/.asdf/shims:/usr/bin:$PATH"
RUN \
    echo 'PATH="/home/vscode/.asdf/shims:/usr/bin:$PATH"' >> ~/.bashrc; \
    echo '# Install Ruby Gems to ~/gems' >> ~/.bashrc; \
    echo 'export GEM_HOME="$HOME/gems"' >> ~/.bashrc; \
    echo 'export PATH="$HOME/gems/bin:$PATH"' >> ~/.bashrc;

ENV PATH="$PATH:/workspaces/eps-assist-me/node_modules/.bin"

# Install ASDF plugins
RUN asdf plugin add python; \
    asdf plugin add poetry https://github.com/asdf-community/asdf-poetry.git; \
    asdf plugin add nodejs https://github.com/asdf-vm/asdf-nodejs.git; \
    asdf plugin add shellcheck https://github.com/luizm/asdf-shellcheck.git; \
    asdf plugin add direnv; \
    asdf plugin add actionlint; \
    asdf plugin add ruby https://github.com/asdf-vm/asdf-ruby.git

WORKDIR /workspaces/eps-assist-me
ADD .tool-versions /workspaces/eps-assist-me/.tool-versions
ADD .tool-versions /home/vscode/.tool-versions

RUN asdf install
