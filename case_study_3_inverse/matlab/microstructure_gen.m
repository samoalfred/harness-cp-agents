%% Equal-grain RVE generator -- paper Application 1 (Yaghoobi et al. 2022)
% Builds the OFHC-copper RVE used for the Taylor model: 400 grains of EQUAL
% size with a RANDOM initial texture, ONE grain per voxel/element on a
% [Nx Ny Nz] grid (default 5x8x10 = 400), mirroring the paper's "400 grains
% with equal sizes" and the RVE structure in CS2_Texture_Evolution.
%
% For the Taylor (mean-field) model only the set of orientations and their
% (equal) weights matter -- grain shape/topology is irrelevant -- so a regular
% one-grain-per-voxel grid is the faithful and efficient representation.
%
% Outputs (consumed by tools/h5_converter.py):
%   input_structure_poly.h5   (/pix = grain ids, /orientation = Rodrigues)
%   output_summary.txt
%   figures/initial_texture.png   (pre-deformation {111}/{100}/{110} pole figures)
%
% Authors: adapted from the U-Michigan microstructure generator
%          (Juyoung Jeong / Veera Sundararaghavan) for CS2_Texture_Evolution_MicroGen.

format compact; clear; close all;
run('C:\Users\samoa\OneDrive - Umich\Documents\MATLAB\mtex-6.0.0\mtex-6.0.0\startup_mtex.m');

%% 1. Configuration (paper Application 1)
rng_seed         = 0;          % fixed seed -> reproducible RVE (same texture every run)
rng(rng_seed);
grid_dims        = [5 8 10];   % Nx Ny Nz  -> 400 grains, one grain per voxel
orientation_type = 'textured';   % paper: random initial texture ('random' | 'textured')
fiber_dir        = [1 1 0];     % used only if 'textured'
sigma_spread     = 27.11764705882353;        % deg scatter, used only if 'textured'

Nx = grid_dims(1); Ny = grid_dims(2); Nz = grid_dims(3);
N_grains = Nx * Ny * Nz;
fprintf('Equal-grain RVE: %dx%dx%d = %d grains (one grain per voxel), texture = %s\n', ...
        Nx, Ny, Nz, N_grains, orientation_type);

%% 2. One grain per voxel: grain id = linear (column-major) index
phase = reshape(uint32(1:N_grains), [Nx Ny Nz]);

%% 3. Orientations (Rodrigues vectors, 3 per grain)
ori_vec = zeros(3*N_grains, 1);

if strcmp(orientation_type, 'random')
    % Uniform random orientations via Shoemake's quaternion sampling.
    for k = 1:N_grains
        u1 = rand(); u2 = rand(); u3 = rand();
        q_w = sqrt(1-u1)*sin(2*pi*u2);
        q_x = sqrt(1-u1)*cos(2*pi*u2);
        q_y = sqrt(u1)  *sin(2*pi*u3);
        q_z = sqrt(u1)  *cos(2*pi*u3);
        if abs(q_w) < 1e-8
            rod = [q_x q_y q_z] / 1e-9;
        else
            rod = [q_x q_y q_z] / q_w;
        end
        ori_vec(3*(k-1)+1 : 3*k) = rod(:);
    end
else  % 'textured' fibre about fiber_dir (kept for flexibility; not used for the paper case)
    c_dir = fiber_dir / norm(fiber_dir);
    s_dir = [0 0 1];
    v = cross(c_dir, s_dir); s = norm(v); c = dot(c_dir, s_dir);
    vx = [0 -v(3) v(2); v(3) 0 -v(1); -v(2) v(1) 0];
    if s < 1e-8, R_base = eye(3); else, R_base = eye(3) + vx + vx^2*((1-c)/s^2); end
    for k = 1:N_grains
        phi = rand()*2*pi;
        R_spin = [cos(phi) -sin(phi) 0; sin(phi) cos(phi) 0; 0 0 1];
        wa = deg2rad(sigma_spread*randn()); aa = rand()*2*pi;
        ax = [cos(aa); sin(aa); 0];
        K = [0 -ax(3) ax(2); ax(3) 0 -ax(1); -ax(2) ax(1) 0];
        R_w = eye(3) + sin(wa)*K + (1-cos(wa))*K*K;
        R = R_spin*R_w*R_base;
        th = acos(max(min((trace(R)-1)/2,1),-1));
        if abs(th) < 1e-6
            rod = [0 0 0];
        else
            ax2 = (1/(2*sin(th)))*[R(3,2)-R(2,3); R(1,3)-R(3,1); R(2,1)-R(1,2)];
            rod = ax2*tan(th/2);
        end
        ori_vec(3*(k-1)+1 : 3*k) = rod(:);
    end
end

%% 4. Save HDF5 (format read by tools/h5_converter.py)
h5filename = 'input_structure_poly.h5';
if isfile(h5filename), delete(h5filename); end
pix_flat = int32(phase(:));
h5create(h5filename, '/pix', [numel(pix_flat) 1], 'Datatype', 'int32');
h5write(h5filename, '/pix', pix_flat);
h5writeatt(h5filename, '/pix', 'dimensions', int32([Nx Ny Nz]));
h5create(h5filename, '/orientation', size(ori_vec), 'Datatype', 'double');
h5write(h5filename, '/orientation', ori_vec);
h5writeatt(h5filename, '/orientation', 'dimensions', int32(size(ori_vec)));
fprintf('Saved HDF5: %s\n', h5filename);

%% 5. Output summary
fid = fopen('output_summary.txt', 'w');
fprintf(fid, 'Equal-grain RVE (paper Application 1, Yaghoobi et al. 2022)\n');
fprintf(fid, 'Grid: %d x %d x %d = %d voxels = %d grains (one grain per voxel, equal sizes)\n', ...
        Nx, Ny, Nz, N_grains, N_grains);
fprintf(fid, 'Orientation type: %s\n', orientation_type);
fprintf(fid, 'Done!\n');
fclose(fid);
disp('Output summary written.');

%% 6. Pre-deformation pole figures of the initial (random) texture
try
    cs = crystalSymmetry('m-3m');
    rods = reshape(ori_vec, 3, N_grains).';
    ori  = orientation.byRodrigues(rods, cs);
    odf  = calcDensity(ori, 'halfwidth', 8*degree);
    setMTEXpref('xAxisDirection','east');
    setMTEXpref('zAxisDirection','outOfPlane');
    fig_dir = fullfile(fileparts(mfilename('fullpath')), 'figures');
    if ~exist(fig_dir,'dir'), mkdir(fig_dir); end
    figure('Visible','off','Position',[100 100 1250 430],'Color','w');
    plotPDF(odf, [Miller(1,1,1,cs), Miller(1,0,0,cs), Miller(1,1,0,cs)], ...
            'smooth', 'resolution', 2*degree, 'upper');
    setColorRange([0 3.5]);
    mtexColorbar;
    print(gcf, fullfile(fig_dir,'initial_texture.png'), '-dpng', '-r150');
    close(gcf);
    fprintf('Saved initial-texture pole figures.\n');
catch ME
    fprintf('WARNING: initial pole-figure plotting skipped: %s\n', ME.message);
end

%% 7. 3D render of the generated RVE (voxels coloured by IPF-Z orientation)
try
    fig_dir = fullfile(fileparts(mfilename('fullpath')), 'figures');
    if ~exist(fig_dir,'dir'), mkdir(fig_dir); end
    cs3 = crystalSymmetry('m-3m');
    rods3 = reshape(ori_vec, 3, N_grains).';
    o3   = orientation.byRodrigues(rods3, cs3);
    key3 = ipfColorKey(cs3);
    key3.inversePoleFigureDirection = vector3d.Z;
    colors = key3.orientation2color(o3);          % N_grains x 3 RGB

    cubeV = [0 0 0;1 0 0;1 1 0;0 1 0;0 0 1;1 0 1;1 1 1;0 1 1];
    cubeF = [1 2 3 4;5 6 7 8;1 2 6 5;2 3 7 6;3 4 8 7;4 1 5 8];
    nVox = Nx*Ny*Nz;
    V = zeros(8*nVox,3); F = zeros(6*nVox,4); C = zeros(6*nVox,3);
    vi = 0; fi = 0;
    for x = 1:Nx
      for y = 1:Ny
        for z = 1:Nz
          g = phase(x,y,z);
          V(vi+1:vi+8,:) = cubeV + [x-1 y-1 z-1];
          F(fi+1:fi+6,:) = cubeF + vi;
          C(fi+1:fi+6,:) = repmat(colors(g,:), 6, 1);
          vi = vi + 8; fi = fi + 6;
        end
      end
    end

    fig3 = figure('Visible','off','Color','w','Position',[100 100 700 900]);
    patch('Vertices',V,'Faces',F,'FaceVertexCData',C,'FaceColor','flat', ...
          'EdgeColor',[0.1 0.1 0.1],'LineWidth',0.25);
    axis equal tight; grid on; box on;
    xlabel('X'); ylabel('Y'); zlabel('Z');
    view([-52 22]); camproj('perspective');
    set(gca,'FontSize',13,'LineWidth',1.0);
    title(sprintf(['Input RVE: %d grains (%dx%dx%d, one grain/voxel)\n' ...
                   'random texture, IPF-Z colouring'], N_grains, Nx, Ny, Nz), ...
          'FontSize', 14, 'FontWeight', 'bold');
    print(fig3, fullfile(fig_dir,'RVE_3D.png'), '-dpng', '-r200');
    close(fig3);
    fprintf('Saved 3D RVE render.\n');
catch ME
    fprintf('WARNING: 3D RVE render skipped: %s\n', ME.message);
end

disp('Microstructure generation done.');
