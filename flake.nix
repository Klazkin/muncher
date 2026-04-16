{
  description = "Python GTK development environment with uv";

  inputs = { nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable"; };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux"; # Standard 64-bit Linux
      pkgs = import nixpkgs { inherit system; };
    in {
      devShells.${system}.default = pkgs.mkShell {
        name = "python-uv-env";

        packages = with pkgs; [
          python3
          uv
          cmake
          cairo
          python313Packages.pycairo
          pkg-config
          gtk4
          gobject-introspection
          libadwaita
          cambalache
          blueprint-compiler
        ];
      };
    };
}
