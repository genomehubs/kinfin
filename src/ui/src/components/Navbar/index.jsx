import React from "react";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import MenuIcon from "@mui/icons-material/Menu";
import Button from "@mui/material/Button";
import { useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { setSelectedClusterSet } from "../../app/store/config/actions";
import BreadcrumbsNav from "../BreadcrumbsNav";

const Navbar = ({ onMenuClick, breadcrumbs = [] }) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="fixed" color="inherit" sx={{ zIndex: 1002 }}>
        <Toolbar>
          <IconButton
            size="large"
            edge="start"
            color="inherit"
            aria-label="menu"
            sx={{ mr: 2 }}
            onClick={onMenuClick}
          >
            <MenuIcon />
          </IconButton>
          <Typography
            variant="h6"
            component="div"
            color="primary"
            sx={{ flexGrow: 1, fontWeight: "bold" }}
          >
            KinFin
          </Typography>
          <Button
            onClick={() => {
              navigate("/define-node-labels");
              dispatch(setSelectedClusterSet(null));
            }}
            color="primary"
            variant="contained"
          >
            New Analysis
          </Button>
        </Toolbar>

        {breadcrumbs.length > 0 && (
          <Toolbar
            variant="dense"
            sx={{ borderTop: "1px solid #ddd", minHeight: "40px" }}
          >
            {" "}
            <BreadcrumbsNav items={breadcrumbs} />
          </Toolbar>
        )}
      </AppBar>
    </Box>
  );
};

export default Navbar;
