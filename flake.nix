{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:nixos/nixpkgs/release-25.05";
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
    deps = with pkgs;( [
      typst
      python313
    ] ++ (with python313Packages; [
      pyhanko
      pymupdf
      pillow
      inquirerpy

      tkinter
    ]));
    in rec {
      devShells.default = with pkgs; mkShellNoCC {
        buildInputs = deps;

        TYPST_FONT_PATHS = "${open-sans}";
        TYPST_IGNORE_SYSTEM_FONTS = "true";
      };
      packages.default = with pkgs; python313Packages.buildPythonApplication {
        pname = "resignation";
        version = "1.0.0";

        src = ./.;

        dependencies = deps;

        preFixup = ''
          makeWrapperArgs+=(--set TYPST_FONT_PATHS ${open-sans})
          makeWrapperArgs+=(--set TYPST_IGNORE_SYSTEM_FONTS true)
        '';
      };

      apps.default = {
        type = "app";
        program = "${packages.default}/bin/resignation.py";
      };
  });
}
