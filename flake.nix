{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:nixos/nixpkgs/release-25.11";
  };

  outputs = {
    self,
    flake-utils,
    nixpkgs,
    ...
  }: with flake-utils.lib;
  eachDefaultSystem (system: let
    pkgs = import nixpkgs {
      inherit system;
    };
    pyPkgs = pkgs.python313Packages;
    deps = with pkgs;( [
      typst
    ] ++ (with pyPkgs; [
      python

      setuptools-scm
      pyhanko
      pymupdf
      pillow
      inquirerpy
      pyqt6
      keyring
    ]));
    version = "nix-" + (self.shortRev or self.dirtyShortRev or "unknown");
    in rec {
      devShells.default = with pkgs; mkShellNoCC {
        buildInputs = deps;

        TYPST_FONT_PATHS = "${open-sans}";
        TYPST_IGNORE_SYSTEM_FONTS = "true";
      };
      packages.default = with pkgs; pyPkgs.buildPythonApplication {
        pname = "resignation";
        pyproject = true;
        version = version;

        src = lib.cleanSourceWith {
          src = ./.;
          filter = path: type:
            let rel = lib.removePrefix (toString ./. + "/") (toString path);
            in rel == "pyproject.toml" || lib.hasPrefix "resignation" rel;
        };

        build-system = with pyPkgs; [
          setuptools
          setuptools-scm
        ];
        dependencies = deps;

        # only necessary for the stamp
        preFixup = ''
          makeWrapperArgs+=(--set TYPST_FONT_PATHS ${open-sans})
          makeWrapperArgs+=(--set TYPST_IGNORE_SYSTEM_FONTS true)
          makeWrapperArgs+=(--set SETUPTOOLS_SCM_PRETEND_VERSION "${version}")
        '';
      };

      apps.default = {
        type = "app";
        program = "${packages.default}/bin/resignation";
      };
  });
}
