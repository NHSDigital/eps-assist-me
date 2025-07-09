FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
  && apt-get -y install --no-install-recommends \
     curl git build-essential libssl-dev zlib1g-dev \
     libbz2-dev libreadline-dev libsqlite3-dev wget llvm \
     libncurses5-dev libncursesw5-dev xz-utils tk-dev \
     liblzma-dev python3-pip libffi-dev

# Set user to vscode
USER vscode

# Install ASDF
RUN git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.11.3; \
    echo '. $HOME/.asdf/asdf.sh' >> ~/.bashrc; \
    echo '. $HOME/.asdf/completions/asdf.bash' >> ~/.bashrc; \
    echo '# Install Ruby Gems to ~/gems' >> ~/.bashrc; \
    echo 'export GEM_HOME="$HOME/gems"' >> ~/.bashrc; \
    echo 'export PATH="$HOME/gems/bin:$PATH"' >> ~/.bashrc;

ENV PATH="$PATH:/home/vscode/.asdf/bin/:/workspaces/eps-assist-me/node_modules/.bin"

# Install ASDF plugins
RUN asdf plugin add python; \
    asdf plugin add poetry https://github.com/asdf-community/asdf-poetry.git; \
    asdf plugin add direnv; \
    asdf plugin add actionlint; \
    asdf plugin add ruby https://github.com/asdf-vm/asdf-ruby.git

# Set working directory
WORKDIR /workspaces/eps-assist-me

# Copy .tool-versions
ADD .tool-versions /workspaces/prescriptionsforpatients/.tool-versions
ADD .tool-versions /home/vscode/.tool-versions

# Install tools
RUN asdf install; \
    asdf reshim python; \
    asdf reshim poetry; \
    asdf direnv setup --shell bash --version 2.32.2;
