function pole_figure(base)
% pole_figure(base)
%   base : the CS4 run folder (contains QuadOut_pass1..N.csv).
% Computes the (0001) pole figure and its maximum intensity for every completed
% pass (deformed Rodrigues in columns 8-10 of the full QuadratureOutputs) and for
% the reference 5-pass simulation (columns 2-4 of the trimmed reference file, path
% read from base/ref_paths.txt). Saves one PNG per pole figure into base and writes
% base/texture_results.txt with lines "pass,max" and "ref5pass,max".
%
% Requires MTEX. This machine has two MTEX installs (6.0.0 and 6.2.beta.3); if both
% are on the path they clash (euler2quat/specimenSymmetry error), so purge all MTEX
% path entries and load a single clean version before use.
p = strsplit(path, pathsep);
mtex_on = p(contains(p,'mtex','IgnoreCase',true));
if ~isempty(mtex_on)
    rmpath(strjoin(mtex_on, pathsep));
end
% MTEX location: set the MTEX_ROOT environment variable to your MTEX install
% directory (the folder containing startup_mtex.m), or edit the fallback below.
root = getenv('MTEX_ROOT');
if isempty(root)
    root = fullfile(getenv('USERPROFILE'), 'OneDrive - Umich', ...
        'Documents', 'MATLAB', 'mtex-6.2.beta.3', 'mtex-6.2.beta.3');
end
addpath(root); run(fullfile(root,'startup_mtex.m'));

cs = crystalSymmetry('6/mmm',[3.21 3.21 5.213],'X||a*','Y||b','Z||c*');
ss = specimenSymmetry('triclinic');
setMTEXpref('xAxisDirection','east'); setMTEXpref('zAxisDirection','outOfPlane');
pfAnn = @(varargin) text([vector3d.X,vector3d.Y],{'TD','RD'}, ...
    'BackgroundColor','w','tag','axesLabels',varargin{:});
setMTEXpref('pfAnnotations',pfAnn);
h = Miller(0,0,0,1,cs);

    function mx = pf_from(file, cols)
        R = readmatrix(file); R = R(:, ~all(isnan(R),1));
        rod = R(:, cols); mg = sqrt(sum(rod.^2,2));
        ori = orientation.byAxisAngle( ...
            vector3d(rod(:,1)./mg, rod(:,2)./mg, rod(:,3)./mg), 2*atan(mg), cs, ss);
        odf = calcDensity(ori,'halfwidth',10*degree,'resolution',5*degree);
        pf  = calcPoleFigure(odf, h, 'resolution',5*degree,'complete');
        mx  = max(max(pf));
    end

res = fopen(fullfile(base,'texture_results.txt'),'w');

% completed passes (mine): columns 8-10
p = 1;
while isfile(fullfile(base, sprintf('QuadOut_pass%d.csv',p)))
    f = fullfile(base, sprintf('QuadOut_pass%d.csv',p));
    mx = pf_from(f, [8 9 10]);
    fig = figure('Color','w','Position',[100 100 460 460]);
    R = readmatrix(f); R = R(:,~all(isnan(R),1)); rod=R(:,8:10); mg=sqrt(sum(rod.^2,2));
    ori = orientation.byAxisAngle(vector3d(rod(:,1)./mg,rod(:,2)./mg,rod(:,3)./mg),2*atan(mg),cs,ss);
    odf = calcDensity(ori,'halfwidth',10*degree,'resolution',5*degree);
    plotPDF(odf,h,'antipodal','resolution',5*degree,'smooth'); mtexColorbar;
    mtexTitle(sprintf('mine pass %d  (max %.2f)',p,mx));
    saveas(fig, fullfile(base, sprintf('pf_mine_pass%d.png',p))); close(fig);
    fprintf(res,'pass%d,%.3f\n',p,mx);
    p = p + 1;
end

% reference 5-pass simulation: path in base/ref_paths.txt (line: REF5=<path>), cols 2-4
refp = '';
if isfile(fullfile(base,'ref_paths.txt'))
    L = readlines(fullfile(base,'ref_paths.txt'));
    for i=1:numel(L)
        if startsWith(L(i),'REF5='), refp = char(extractAfter(L(i),'REF5=')); end
    end
end
if ~isempty(refp) && isfile(refp)
    mx = pf_from(refp, [2 3 4]);
    fig = figure('Color','w','Position',[100 100 460 460]);
    R = readmatrix(refp); R = R(:,~all(isnan(R),1)); rod=R(:,2:4); mg=sqrt(sum(rod.^2,2));
    ori = orientation.byAxisAngle(vector3d(rod(:,1)./mg,rod(:,2)./mg,rod(:,3)./mg),2*atan(mg),cs,ss);
    odf = calcDensity(ori,'halfwidth',10*degree,'resolution',5*degree);
    plotPDF(odf,h,'antipodal','resolution',5*degree,'smooth'); mtexColorbar;
    mtexTitle(sprintf('authors 5-pass sim  (max %.2f)',mx));
    saveas(fig, fullfile(base,'pf_authors_5pass.png')); close(fig);
    fprintf(res,'ref5pass,%.3f\n',mx);
end
fclose(res);
end
