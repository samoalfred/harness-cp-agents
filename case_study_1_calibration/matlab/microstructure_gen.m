%% Synthetic 3D Microstructure Generator for ELAS3D-Xtal
% Generates realistic 3D voxelized polycrystals with columnar or equiaxed
% grains and optional process-induced defects (pores).
% Outputs: input_structure_poly.h5, output_summary.txt, figures/
%
% Authors:       Juyoung Jeong and Veera Sundararaghavan
% Affiliation:   Department of Aerospace Engineering, University of Michigan
% Modified for SS316L_Pipeline agentic workflow.

format compact; clear; close all;
tStart = tic;

% Initialize MTEX (required for IPF coloring and pole figures)
run('C:\Users\samoa\OneDrive - Umich\Documents\MATLAB\mtex-6.0.0\mtex-6.0.0\startup_mtex.m');

%% 1. Configuration & Parameters
% NOTE: Calibration-scale configuration. A small 32x32x32 grid is used so
% each PRISMS-Plasticity simulation is cheap enough to run the full
% calibration budget (~60 simulations). grid_num = 31 -> 32 voxels per side.
% mean_d is enlarged accordingly so the domain holds ~350 well-resolved
% grains rather than thousands of unresolved ones.
% --- Domain Variables ---
max_len = 1;           % [mm] max_len: Absolute maximum physical length allowed for the domain boundaries.
cube_len = 1;          % [mm] cube_len: The actual physical side length of the cubic domain being generated.
grid_num = 31;          % [voxels] grid_num: Number of voxels along each 1D edge of the cube (Resolution).
dx = cube_len/grid_num;  % [mm] dx: The physical length of a single voxel edge.
xmin = 0;                % [mm] xmin: Lower boundary of the domain on the X-axis (Origin).
ymin = 0;                % [mm] ymin: Lower boundary of the domain on the Y-axis (Origin).
zmin = 0;                % [mm] zmin: Lower boundary of the domain on the Z-axis (Origin).

% --- Grain Statistics Variables ---
mean_d = 0.055;        % [mm] mean_d: Target average equivalent diameter of the grains in the XY plane.
std_d  = 0.35*mean_d;  % [mm] std_d: Standard deviation of the grain diameter (controls size variability). 0.35*mean_d


% Aspect ratio variables (defines if grains are equiaxed (~1.0) or columnar (>1.0))
mean_aspect = 1;              % [ratio] mean_aspect: Average length-to-width ratio of the grains. mean_aspect = 3.18;
%std_aspect = 0.0025 * mean_aspect; % [ratio] std_aspect: Standard deviation of the aspect ratio. std_aspect = 0.25 * mean_aspect
std_aspect = 0.000001; % [ratio] std_aspect: Standard deviation of the aspect ratio. std_aspect = 0.25 * mean_aspect

% --- Orientation Settings Variables ---
orientation_type = 'random'; % [string] orientation_type: 'textured' for aligned orientations, or 'random'.
sigma_spread = 10;             % [degrees] sigma_spread: If 'textured', defines how much orientations can deviate from the primary axis. %sigma_spread = 15;

pore_type        = 'EOS';
desc             = 'Spherical Gas Pore';

save_data        = 'on';
elas3d_input     = 'on';
phase_data_type  = 'uint32';

stride                 = 1;
microstructure3d_type  = 'surface';
max_pores_show         = 1;
num_grains_iso         = 10;
micro_plot             = 'on';
K_grain                = 2000;

pore             = 'off';
input_pore_file  = 'Defect_Locations_EOS.xlsx';

% Figure output directory (relative to this script's location)
fig_dir = fullfile(fileparts(mfilename('fullpath')), 'figures');
if ~exist(fig_dir, 'dir'), mkdir(fig_dir); end

%% 2. Pore Data
if strcmp(pore, 'on')
    data       = readmatrix(input_pore_file);
    x_pore     = data(:,9);
    y_pore     = data(:,10);
    z_pore     = data(:,11);
    d          = data(:,8);
    r          = d / 2;
    V_pore     = data(:,7);
    D_Feret_max = data(:,12);
    N_pores    = numel(x_pore);
elseif strcmp(pore, 'off')
    x_pore = []; y_pore = []; z_pore = [];
    d = []; r = []; V_pore = []; D_Feret_max = [];
    N_pores = 0;
    warning('No pore file found. Proceeding with no pores.');
end

%% 3. Computational Domain
cube_len   = min(cube_len, max_len);
xmax = xmin + cube_len;
ymax = ymin + cube_len;
zmax = zmin + cube_len;
cuboid_size = [xmax-xmin, ymax-ymin, zmax-zmin];

xvec = xmin:dx:xmax; Nx = length(xvec);
yvec = ymin:dx:ymax; Ny = length(yvec);
zvec = zmin:dx:zmax; Nz = length(zvec);

[X, Y, Z]  = ndgrid(xvec, yvec, zvec);
domain_vol = prod(cuboid_size);

%% 4. Lognormal Grain Size and Aspect Ratio
mean_grain_vol = pi * (mean_d/2)^2 * (mean_aspect * mean_d);
N_grains       = ceil(domain_vol / mean_grain_vol);

sigma_log  = sqrt(log((std_d/mean_d)^2 + 1));
mu_log     = log(mean_d) - 0.5*sigma_log^2;
grain_diameters = lognrnd(mu_log, sigma_log, N_grains, 1);
r_xy       = grain_diameters / 2;

sigma_log_a = sqrt(log((std_aspect/mean_aspect)^2 + 1));
mu_log_a    = log(mean_aspect) - 0.5*sigma_log_a^2;
aspect_ratios = lognrnd(mu_log_a, sigma_log_a, N_grains, 1);
r_z         = aspect_ratios .* r_xy;

grain_seeds = [rand(N_grains,1)*cuboid_size(1)+xmin, ...
               rand(N_grains,1)*cuboid_size(2)+ymin, ...
               rand(N_grains,1)*cuboid_size(3)+zmin];

%% 5. Anisotropic Assignment
fprintf('\n=== PARALLEL + SPATIAL FILTERING MICROSTRUCTURE GENERATION ===\n');
main_timer = tic;

if isempty(gcp('nocreate'))
    fprintf('Starting parallel pool...\n');
    pool_timer  = tic;
    num_workers = feature('numcores');
    parpool('local', num_workers);
    fprintf('Parallel pool started in %.1fs with %d workers\n', toc(pool_timer), gcp().NumWorkers);
else
    fprintf('Using existing parallel pool with %d workers\n', gcp().NumWorkers);
end

phase        = zeros(Nx, Ny, Nz, phase_data_type);
inv_r_xy2    = single(1 ./ (r_xy.^2));
inv_r_z2     = single(1 ./ (r_z.^2));
grain_seeds_single = single(grain_seeds);

fprintf('\nBuilding spatial acceleration structure...\n');
accel_timer  = tic;
grid_res     = 15;
x_edges = linspace(min(xvec), max(xvec), grid_res+1);
y_edges = linspace(min(yvec), max(yvec), grid_res+1);
z_edges = linspace(min(zvec), max(zvec), grid_res+1);
max_influence = max([r_xy(:); r_z(:)]) * 1.5;
total_cells   = grid_res^3;
spatial_grid_temp = cell(total_cells, 1);

parfor linear_idx = 1:total_cells
    [i, j, k] = ind2sub([grid_res, grid_res, grid_res], linear_idx);
    cell_xmin = x_edges(i); cell_xmax = x_edges(i+1);
    cell_ymin = y_edges(j); cell_ymax = y_edges(j+1);
    cell_zmin = z_edges(k); cell_zmax = z_edges(k+1);
    relevant_grains = find(...
        grain_seeds_single(:,1) >= (cell_xmin - max_influence) & ...
        grain_seeds_single(:,1) <= (cell_xmax + max_influence) & ...
        grain_seeds_single(:,2) >= (cell_ymin - max_influence) & ...
        grain_seeds_single(:,2) <= (cell_ymax + max_influence) & ...
        grain_seeds_single(:,3) >= (cell_zmin - max_influence) & ...
        grain_seeds_single(:,3) <= (cell_zmax + max_influence));
    spatial_grid_temp{linear_idx} = relevant_grains;
end

spatial_grid = cell(grid_res, grid_res, grid_res);
for linear_idx = 1:total_cells
    [i, j, k] = ind2sub([grid_res, grid_res, grid_res], linear_idx);
    spatial_grid{i,j,k} = spatial_grid_temp{linear_idx};
end
clear spatial_grid_temp;
fprintf('Spatial acceleration structure built in %.1fs\n', toc(accel_timer));

block_size  = 50;
n_blocks_x  = ceil(Nx / block_size);
n_blocks_y  = ceil(Ny / block_size);
n_blocks_z  = ceil(Nz / block_size);
total_blocks = n_blocks_x * n_blocks_y * n_blocks_z;
fprintf('Processing %d blocks (%dx%dx%d) in parallel:\n', total_blocks, n_blocks_x, n_blocks_y, n_blocks_z);

num_workers       = gcp().NumWorkers;
blocks_per_batch  = max(1, floor(total_blocks / (num_workers * 4)));
n_batches         = ceil(total_blocks / blocks_per_batch);
fprintf('Using %d batches of %d blocks each\n', n_batches, blocks_per_batch);

completed_blocks      = 0;
total_grains_processed = 0;
blocks_with_grains    = 0;
batch_times           = [];

fprintf('\nStarting parallel processing:\n');
process_timer = tic;

for batch_idx = 1:n_batches
    batch_timer = tic;
    batch_start = (batch_idx - 1) * blocks_per_batch + 1;
    batch_end   = min(batch_idx * blocks_per_batch, total_blocks);
    current_batch_size = batch_end - batch_start + 1;

    block_list_batch = zeros(current_batch_size, 4);
    for local_idx = 1:current_batch_size
        block_num = batch_start + local_idx - 1;
        bz = ceil(block_num / (n_blocks_x * n_blocks_y));
        remaining = block_num - (bz-1) * n_blocks_x * n_blocks_y;
        by = ceil(remaining / n_blocks_x);
        bx = remaining - (by-1) * n_blocks_x;
        block_list_batch(local_idx, :) = [bx, by, bz, block_num];
    end

    batch_results     = cell(current_batch_size, 1);
    batch_indices     = cell(current_batch_size, 1);
    batch_grain_counts = zeros(current_batch_size, 1);

    xvec_local = xvec; yvec_local = yvec; zvec_local = zvec;
    x_edges_local = x_edges; y_edges_local = y_edges; z_edges_local = z_edges;

    parfor local_idx = 1:current_batch_size
        bx = block_list_batch(local_idx, 1);
        by = block_list_batch(local_idx, 2);
        bz = block_list_batch(local_idx, 3);

        ix1 = (bx-1)*block_size + 1; ix2 = min(bx*block_size, Nx);
        iy1 = (by-1)*block_size + 1; iy2 = min(by*block_size, Ny);
        iz1 = (bz-1)*block_size + 1; iz2 = min(bz*block_size, Nz);

        block_xmin = xvec_local(ix1); block_xmax = xvec_local(ix2);
        block_ymin = yvec_local(iy1); block_ymax = yvec_local(iy2);
        block_zmin = zvec_local(iz1); block_zmax = zvec_local(iz2);

        relevant_grains = find(...
            grain_seeds_single(:,1) >= (block_xmin - max_influence) & ...
            grain_seeds_single(:,1) <= (block_xmax + max_influence) & ...
            grain_seeds_single(:,2) >= (block_ymin - max_influence) & ...
            grain_seeds_single(:,2) <= (block_ymax + max_influence) & ...
            grain_seeds_single(:,3) >= (block_zmin - max_influence) & ...
            grain_seeds_single(:,3) <= (block_zmax + max_influence));

        if ~isempty(relevant_grains)
            [Xb, Yb, Zb] = ndgrid(single(xvec_local(ix1:ix2)), ...
                                   single(yvec_local(iy1:iy2)), ...
                                   single(zvec_local(iz1:iz2)));
            block_phase = zeros(size(Xb), 'uint32');
            min_dist2   = inf(size(Xb), 'single');

            for k = relevant_grains'
                dX = Xb - grain_seeds_single(k,1);
                dY = Yb - grain_seeds_single(k,2);
                dZ = Zb - grain_seeds_single(k,3);
                current_dist2 = (dX.^2)*inv_r_xy2(k) + (dY.^2)*inv_r_xy2(k) + (dZ.^2)*inv_r_z2(k);
                update_mask   = current_dist2 < min_dist2;
                block_phase(update_mask) = k;
                min_dist2(update_mask)   = current_dist2(update_mask);
            end

            batch_results{local_idx}     = block_phase;
            batch_indices{local_idx}     = [ix1, ix2, iy1, iy2, iz1, iz2];
            batch_grain_counts(local_idx) = length(relevant_grains);
        else
            batch_results{local_idx} = [];
            batch_indices{local_idx} = [ix1, ix2, iy1, iy2, iz1, iz2];
            batch_grain_counts(local_idx) = 0;
        end
    end

    batch_grains_processed   = 0;
    batch_blocks_with_grains = 0;
    for local_idx = 1:current_batch_size
        if ~isempty(batch_results{local_idx})
            indices = batch_indices{local_idx};
            phase(indices(1):indices(2), indices(3):indices(4), indices(5):indices(6)) = ...
                cast(batch_results{local_idx}, phase_data_type);
            batch_blocks_with_grains = batch_blocks_with_grains + 1;
        end
        batch_grains_processed = batch_grains_processed + batch_grain_counts(local_idx);
    end

    completed_blocks       = completed_blocks + current_batch_size;
    total_grains_processed = total_grains_processed + batch_grains_processed;
    blocks_with_grains     = blocks_with_grains + batch_blocks_with_grains;
    batch_time   = toc(batch_timer);
    batch_times(end+1) = batch_time;
    progress_pct = 100 * completed_blocks / total_blocks;
    elapsed_total = toc(main_timer);
    avg_grains_per_block = batch_grains_processed / current_batch_size;

    if batch_idx > 1
        avg_batch_time   = mean(batch_times);
        remaining_batches = n_batches - batch_idx;
        eta_seconds      = remaining_batches * avg_batch_time;
    else
        eta_seconds = batch_time * (n_batches - 1);
    end

    fprintf('Batch %d/%d: %.1f%% | %.1f grains/block | Elapsed: %.1fs | ETA: %.1fs\n', ...
        batch_idx, n_batches, progress_pct, avg_grains_per_block, elapsed_total, eta_seconds);
end

total_time = toc(main_timer);
fprintf('\n=== COMPLETION SUMMARY ===\n');
fprintf('Total time: %.1f seconds (%.2f minutes)\n', total_time, total_time/60);

unassigned = sum(phase(:) == 0);
if unassigned > 0
    fprintf('WARNING: %d unassigned voxels detected!\n', unassigned);
else
    fprintf('SUCCESS: All voxels assigned.\n');
end

%% 6. Overwrite With Pore Regions
sz_phase = size(phase);
Nx = sz_phase(1); Ny = sz_phase(2); Nz = sz_phase(3);
pore_linear_indices = cell(N_pores, 1);

if ~isempty(x_pore)
    fprintf('Inserting %d Gas Voids...\n', N_pores);
    for k = 1:N_pores
        r_pore = d(k) / 2.0;
        if r_pore <= 0 || isnan(r_pore), continue; end
        buffer = 1.1; max_r = r_pore * buffer;
        idx_x = find(xvec >= x_pore(k)-max_r & xvec <= x_pore(k)+max_r);
        idx_y = find(yvec >= y_pore(k)-max_r & yvec <= y_pore(k)+max_r);
        idx_z = find(zvec >= z_pore(k)-max_r & zvec <= z_pore(k)+max_r);
        if isempty(idx_x) || isempty(idx_y) || isempty(idx_z), continue; end
        [X_sub, Y_sub, Z_sub] = ndgrid(xvec(idx_x), yvec(idx_y), zvec(idx_z));
        mask_sub = ((X_sub-x_pore(k)).^2 + (Y_sub-y_pore(k)).^2 + (Z_sub-z_pore(k)).^2) <= r_pore^2;
        [ii, jj, kk] = ind2sub(size(mask_sub), find(mask_sub));
        if ~isempty(ii)
            pore_linear_indices{k} = sub2ind(sz_phase, ...
                double(idx_x(ii(:))), double(idx_y(jj(:))), double(idx_z(kk(:))));
        end
    end
    all_inds = vertcat(pore_linear_indices{:});
    phase(all_inds) = N_grains + 1;
    nphase = N_grains + 1;
    fprintf('Pore assignment complete: %d voxels\n', numel(all_inds));
else
    nphase = N_grains;
    fprintf('No gas voids.\n');
end

%% 7. Assign Orientations
ori_vec = zeros(3*N_grains, 1);

if strcmp(orientation_type, 'textured')
    fprintf('Generating [1 0 1] Fiber Texture\n');
    c_dir = [1 0 1] / norm([1 0 1]);
    s_dir = [0 0 1];
    v  = cross(c_dir, s_dir);
    s  = norm(v);
    c  = dot(c_dir, s_dir);
    vx = [0 -v(3) v(2); v(3) 0 -v(1); -v(2) v(1) 0];
    if s < 1e-8
        R_base = eye(3);
    else
        R_base = eye(3) + vx + vx^2*((1-c)/s^2);
    end
    for k = 1:N_grains
        phi = rand() * 2*pi;
        R_spin = [cos(phi) -sin(phi) 0; sin(phi) cos(phi) 0; 0 0 1];
        wobble_ang = deg2rad(sigma_spread * randn());
        wb_ax_ang  = rand() * 2*pi;
        ax_w = [cos(wb_ax_ang); sin(wb_ax_ang); 0];
        K    = [0 -ax_w(3) ax_w(2); ax_w(3) 0 -ax_w(1); -ax_w(2) ax_w(1) 0];
        R_wobble = eye(3) + sin(wobble_ang)*K + (1-cos(wobble_ang))*K*K;
        R_total  = R_spin * R_wobble * R_base;
        tr    = trace(R_total);
        theta = acos(max(min((tr-1)/2, 1), -1));
        if abs(theta) < 1e-6
            rod = [0 0 0];
        else
            r_axis = (1/(2*sin(theta))) * ...
                [R_total(3,2)-R_total(2,3); R_total(1,3)-R_total(3,1); R_total(2,1)-R_total(1,2)];
            rod = r_axis * tan(theta/2);
        end
        idx = 3*(k-1)+1;
        ori_vec(idx:idx+2) = rod(:);
    end

elseif strcmp(orientation_type, 'random')
    fprintf('Generating Random Texture\n');
    for k = 1:N_grains
        u1 = rand(); u2 = rand(); u3 = rand();
        q_w = sqrt(1-u1)*sin(2*pi*u2);
        q_x = sqrt(1-u1)*cos(2*pi*u2);
        q_y = sqrt(u1)*sin(2*pi*u3);
        q_z = sqrt(u1)*cos(2*pi*u3);
        if abs(q_w) < 1e-8
            rod_vec = [q_x q_y q_z] / 1e-9;
        else
            rod_vec = [q_x q_y q_z] / q_w;
        end
        idx = 3*(k-1)+1;
        ori_vec(idx:idx+2) = rod_vec;
    end
end

%% 8. Save To HDF5  (always runs first — critical output before any optional steps)
n_phases = max(phase(:));

% HDF5 first — this is what the Python pipeline needs
if strcmp(elas3d_input, 'on')
    h5filename = 'input_structure_poly.h5';
    if isfile(h5filename), delete(h5filename); end
    pix_flat = int32(phase(:));
    h5create(h5filename, '/pix', [length(pix_flat) 1], 'Datatype', 'int32');
    h5write(h5filename, '/pix', pix_flat);
    h5writeatt(h5filename, '/pix', 'dimensions', int32([Nx Ny Nz]));
    h5create(h5filename, '/orientation', size(ori_vec), 'Datatype', 'double');
    h5write(h5filename, '/orientation', ori_vec);
    h5writeatt(h5filename, '/orientation', 'dimensions', int32(size(ori_vec)));
    disp(['Saved HDF5: ', h5filename]);
end

% .mat saves are optional — large files can fail on WSL network paths
if strcmp(save_data, 'on')
    try
        save('xct_poly_params_SS316L.mat', 'xvec','yvec','zvec','Nx','Ny','Nz', ...
            'cube_len','N_grains','n_phases');
        fprintf('Saved params .mat\n');
    catch ME
        fprintf('WARNING: Small .mat save failed: %s\n', ME.message);
    end
    try
        save('xct_poly_params_SS316L_full.mat', '-v7.3');
        fprintf('Saved full workspace .mat\n');
    catch ME
        fprintf('WARNING: Full .mat save failed (large file on WSL path): %s\n', ME.message);
    end
end

%% 9. IPF Coloring (MTEX)
cmap_ipf = [];   % default — filled below if MTEX succeeds
try
    cs   = crystalSymmetry('m-3m');
    rods = reshape(ori_vec(1:3*N_grains), [3, N_grains])';
    if strcmp(orientation_type, 'textured')
        ori_mtex = orientation.byRodrigues(rods, cs);
        RD       = vector3d.Z;
        ipf_key  = ipfHSVKey(cs);
        ipf_key.inversePoleFigureDirection = RD;
        cmap_ipf = ipf_key.orientation2color(ori_mtex);
    elseif strcmp(orientation_type, 'random')
        ori_mtex = orientation('rodrigues', rods, cs);
        ipf_key  = ipfColorKey(cs);
        ipf_key.inversePoleFigureDirection = vector3d.Z;
        cmap_ipf = ipf_key.orientation2color(ori_mtex);
    end
    fprintf('IPF coloring computed successfully.\n');
catch ME
    fprintf('WARNING: MTEX IPF coloring failed: %s\n', ME.message);
    fprintf('Figures will use default colormap instead.\n');
    % Fallback: assign random colors per grain
    cmap_ipf = hsv(N_grains);
end

%% 10. Output Summary
fid = fopen('output_summary.txt', 'w');
fprintf(fid, 'Total number of Grains: %d, Pores: %d\n', N_grains, nphase-N_grains);
fprintf(fid, 'Domain size: %.1f x %.1f x %.1f mm^3\n', cuboid_size(1), cuboid_size(2), cuboid_size(3));
fprintf(fid, 'Domain grid: %d x %d x %d = %d voxels\n', Nx, Ny, Nz, Nx*Ny*Nz);
fprintf(fid, 'Voxel size: %.5f mm (%.2f um)\n', dx, dx*1e3);
num_vox_grain = sum(phase(:) >= 1 & phase(:) <= N_grains);
num_vox_pore  = sum(phase(:) == (N_grains+1));
num_vox_total = numel(phase);
fprintf(fid, 'Grain voxels: %d (%.3f%%)\n', num_vox_grain, 100*num_vox_grain/num_vox_total);
fprintf(fid, 'Pore  voxels: %d (%.3f%%)\n', num_vox_pore,  100*num_vox_pore/num_vox_total);
fprintf(fid, 'Total voxels: %d\n', num_vox_total);
fprintf(fid, 'Mean grain size (XY): %.2f um\n', mean(grain_diameters)*1e3);
fprintf(fid, 'Mean aspect ratio (Z/XY): %.2f\n', mean(aspect_ratios));
fprintf(fid, 'Done!\n');
fclose(fid);
disp('Output summary written.');

%% 11. Plot & Save Figures
if strcmp(micro_plot, 'on')
try

    % --- Fig 1: XY Cross-section ---
    fig1 = figure('Visible','off'); clf;
    s = squeeze(phase(:,:,Nz));
    imagesc(xvec, yvec, s'); set(gca,'YDir','normal'); axis equal tight;
    colormap(cmap_ipf); set(gca,'CLim',[1 size(cmap_ipf,1)]);
    xlabel('X [mm]'); ylabel('Y [mm]');
    title('Top Surface: XY Plane (Z = max)');
    set(gca,'FontSize',15,'LineWidth',1.1,'Box','on');
    saveas(fig1, fullfile(fig_dir, 'fig_XY_crosssection.png'));
    close(fig1);

    % --- Fig 2: YZ Cross-section ---
    fig2 = figure('Visible','off'); clf;
    s = squeeze(phase(1,:,:));
    imagesc(yvec, zvec, s'); set(gca,'XDir','reverse','YDir','normal'); axis equal tight;
    colormap(cmap_ipf); set(gca,'CLim',[1 size(cmap_ipf,1)]);
    xlabel('Y [mm]'); ylabel('Z [mm]');
    title('Left Surface: YZ Plane (X = min)');
    set(gca,'FontSize',15,'LineWidth',1.1,'Box','on');
    saveas(fig2, fullfile(fig_dir, 'fig_YZ_crosssection.png'));
    close(fig2);

    % --- Fig 3: XZ Cross-section ---
    fig3 = figure('Visible','off'); clf;
    s = squeeze(phase(:,1,:));
    imagesc(xvec, zvec, s'); set(gca,'YDir','normal'); axis equal tight;
    colormap(cmap_ipf); set(gca,'CLim',[1 size(cmap_ipf,1)]);
    xlabel('X [mm]'); ylabel('Z [mm]');
    title('Front Surface: XZ Plane (Y = min)');
    set(gca,'FontSize',15,'LineWidth',1.1,'Box','on');
    saveas(fig3, fullfile(fig_dir, 'fig_XZ_crosssection.png'));
    close(fig3);

    % --- Fig 4: 3D Microstructure ---
    if strcmp(microstructure3d_type, 'surface')
        fig4 = figure('Visible','off'); clf; hold on;
        surface_mask = false(Nx,Ny,Nz);
        surface_mask(1,:,:) = true; surface_mask(Nx,:,:) = true;
        surface_mask(:,1,:) = true; surface_mask(:,Ny,:)  = true;
        surface_mask(:,:,1) = true; surface_mask(:,:,Nz)  = true;
        phase_flat   = phase(:);
        X_flat = X(:); Y_flat = Y(:); Z_flat = Z(:);
        surface_inds = find(surface_mask(:));
        surface_inds = surface_inds(1:stride:end);
        grain_inds   = phase_flat(surface_inds);
        valid        = grain_inds >= 1 & grain_inds <= size(cmap_ipf,1);
        surface_inds = surface_inds(valid);
        grain_inds   = grain_inds(valid);
        pt_colors    = cmap_ipf(grain_inds, :);
        scatter3(X_flat(surface_inds), Y_flat(surface_inds), Z_flat(surface_inds), ...
            9, pt_colors, 'filled','MarkerFaceAlpha',0.7,'MarkerEdgeAlpha',0);
        hx = xlabel('X_1 (mm)'); set(hx,'Rotation',21);
        hy = ylabel('X_2 (mm)'); set(hy,'Rotation',-21);
        zlabel('X_3 (mm)');
        title('3D Grain Microstructure (IPF color FCC [101] RD)');
        view([-42.71 22.97]); axis equal tight; grid on; box on;
        set(gca,'FontSize',15,'LineWidth',1.2);
        saveas(fig4, fullfile(fig_dir, 'fig_3D_microstructure.png'));
        close(fig4);
    end

    % --- Fig 5: Grain Size Histogram (XY section) ---
    iz_mid = round(Nz/2);
    phase_xy   = squeeze(phase(:,:,iz_mid));
    grain_ids  = unique(phase_xy(:));
    grain_ids(grain_ids == N_grains+1) = [];
    grain_areas = zeros(numel(grain_ids),1);
    for k = 1:numel(grain_ids)
        grain_areas(k) = sum(phase_xy(:) == grain_ids(k)) * dx * dx;
    end
    grain_diam_xy_um = 2*sqrt(grain_areas/pi) * 1e3;

    fig5 = figure('Visible','off'); clf;
    skewness_val = skewness(grain_diam_xy_um);
    num_bin = ceil(1 + log2(numel(grain_diam_xy_um)) + ...
        log2(1 + abs(skewness_val)/sqrt(6/numel(grain_diam_xy_um))));
    histogram(grain_diam_xy_um, num_bin, 'Normalization','pdf', ...
        'FaceAlpha',0.3,'FaceColor',[0.2 0.8 0.2],'EdgeColor','k');
    hold on;
    pd_xy = fitdist(grain_diam_xy_um,'Lognormal');
    xfit  = linspace(0, max(grain_diam_xy_um)*1.05, 200);
    plot(xfit, pdf(pd_xy, xfit), 'b-', 'LineWidth',3);
    xlabel('Grain diameter [\mum]','FontSize',15);
    ylabel('Probability density','FontSize',15);
    title('Grain Size: XY Section','FontSize',15);
    set(gca,'FontSize',15);
    saveas(fig5, fullfile(fig_dir, 'fig_grainsize_XY.png'));
    close(fig5);

    % --- Fig 6: Grain Size Histogram (3D input) ---
    grain_diam_in_um = grain_diameters * 1e3;
    fig6 = figure('Visible','off'); clf;
    skewness_val = skewness(grain_diam_in_um);
    num_bin = ceil(1 + log2(numel(grain_diam_in_um)) + ...
        log2(1 + abs(skewness_val)/sqrt(6/numel(grain_diam_in_um))));
    histogram(grain_diam_in_um, num_bin, 'Normalization','pdf', ...
        'FaceAlpha',0.6,'FaceColor',[0.2 0.8 0.2],'EdgeColor','k');
    hold on;
    pd_in = fitdist(grain_diam_in_um,'Lognormal');
    xfit  = linspace(0, max(grain_diam_in_um), 200);
    plot(xfit, pdf(pd_in, xfit), 'r-', 'LineWidth',2);
    xlabel('Grain diameter [\mum]','FontSize',15);
    ylabel('Probability density','FontSize',15);
    title('Grain Size: 3D Input','FontSize',15);
    set(gca,'FontSize',15);
    saveas(fig6, fullfile(fig_dir, 'fig_grainsize_3D.png'));
    close(fig6);

    % --- Fig 7-10: Pre-Deformation Pole Figures (individual + combined) ---
    try
        N_ori = numel(ori_vec) / 3;
        K     = min(K_grain, N_ori);
        idx_grains = randperm(N_ori, K);
        ori_idx    = bsxfun(@plus, 3*(idx_grains'-1), (1:3));
        ori_idx    = ori_idx'; ori_idx = ori_idx(:);
        ori_vec_matrix = reshape(ori_vec(ori_idx), 3, []).';
        cs_pf  = crystalSymmetry('m-3m');
        ori_pf = orientation.byRodrigues(ori_vec_matrix, cs_pf);
        psi    = SO3vonMisesFisherKernel('halfwidth', 5*degree);
        odf    = unimodalODF(ori_pf, psi);
        setMTEXpref('xAxisDirection','east');
        setMTEXpref('zAxisDirection','outOfPlane');

        % Individual pole figures for side-by-side comparison
        fig_pre100 = figure('Visible','off'); clf;
        plotPDF(odf, Miller(1,0,0,cs_pf), 'antipodal','contourf','smooth','resolution',1*degree,'minmax');
        colorbar; title('{100} Pole Figure - Pre Deformation','FontSize',14);
        saveas(fig_pre100, fullfile(fig_dir, 'pre_pf100.png')); close(fig_pre100);

        fig_pre110 = figure('Visible','off'); clf;
        plotPDF(odf, Miller(1,1,0,cs_pf), 'antipodal','contourf','smooth','resolution',1*degree,'minmax');
        colorbar; title('{110} Pole Figure - Pre Deformation','FontSize',14);
        saveas(fig_pre110, fullfile(fig_dir, 'pre_pf110.png')); close(fig_pre110);

        fig_pre111 = figure('Visible','off'); clf;
        plotPDF(odf, Miller(1,1,1,cs_pf), 'antipodal','contourf','smooth','resolution',1*degree,'minmax');
        colorbar; title('{111} Pole Figure - Pre Deformation','FontSize',14);
        saveas(fig_pre111, fullfile(fig_dir, 'pre_pf111.png')); close(fig_pre111);

        % Combined figure (all 3 in one)
        fig7 = figure('Visible','off'); clf;
        plotPDF(odf, [Miller(1,0,0,cs_pf), Miller(1,1,0,cs_pf), Miller(1,1,1,cs_pf)], ...
            'antipodal','contourf','smooth','resolution',1*degree,'minmax');
        colorbar;
        saveas(fig7, fullfile(fig_dir, 'fig_pole_figure.png')); close(fig7);

        % Inverse pole figure
        fig8 = figure('Visible','off'); clf;
        plotIPDF(odf, [xvector, yvector, zvector], 'antipodal');
        saveas(fig8, fullfile(fig_dir, 'fig_inverse_pole_figure.png')); close(fig8);

        fprintf('Pre-deformation pole figures saved.\n');
    catch ME
        fprintf('WARNING: Pole figure plotting failed: %s\n', ME.message);
    end

    fprintf('All figures saved to: %s\n', fig_dir);
catch ME
    fprintf('WARNING: Figure generation failed: %s\n', ME.message);
end
end

%% Final timing
disp('Done!');
tElapsed = toc(tStart);
fprintf('\nTotal computation time: %.2f seconds (%.2f minutes)\n', tElapsed, tElapsed/60);
