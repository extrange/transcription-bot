{
  pkgs,
  config,
  ...
}:

{
  # Python is provided by Nix, while uv owns the virtualenv and dependencies.
  # The venv lives in .devenv/state/venv, not in the repository's .venv.
  languages.python = {
    enable = true;
    package = pkgs.python315;
    venv.enable = true;
    uv = {
      enable = true;
      sync = {
        enable = true;
        # Keep uv.lock authoritative; the uv-lock hook updates it explicitly.
        arguments = [ "--locked" ];
      };
    };
  };

  # ffprobe is used to measure media duration; git is needed by git-hooks.
  packages = with pkgs; [
    ffmpeg
    git
  ];

  # Keep uv's cache inside the repository state so it does not depend on $HOME.
  env.UV_CACHE_DIR = "${config.env.DEVENV_STATE}/uv-cache";

  # Replaces .pre-commit-config.yaml. Hooks call the project-locked tools from
  # the devenv virtualenv, so local and CI results stay in sync.
  git-hooks.hooks = {
    trim-trailing-whitespace.enable = true;
    end-of-file-fixer.enable = true;
    check-yaml.enable = true;
    check-added-large-files.enable = true;
    check-case-conflicts.enable = true;
    actionlint.enable = true;
    trufflehog.enable = true;
    nixfmt.enable = true;

    ruff = {
      enable = true;
      entry = "${config.env.DEVENV_STATE}/venv/bin/ruff check --fix";
    };
    ruff-format = {
      enable = true;
      entry = "${config.env.DEVENV_STATE}/venv/bin/ruff format";
    };
    pyright = {
      enable = true;
      # Hooks can run outside `devenv shell`, so pass the interpreter explicitly.
      settings.binPath = "${config.env.DEVENV_STATE}/venv/bin/pyright --pythonpath ${config.env.DEVENV_STATE}/venv/bin/python";
      pass_filenames = false;
    };
    uv-lock = {
      enable = true;
      entry = "env UV_CACHE_DIR=${config.env.DEVENV_STATE}/uv-cache ${config.languages.python.uv.package}/bin/uv lock";
    };
  };
}
